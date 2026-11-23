import math
import os
import json
import hashlib
import re
import copy
import subprocess
import uuid
from typing import Dict, List, Any, Tuple, Optional, Callable
from dataclasses import dataclass
from .protocol_freeze import (
    SourcePairFeatures, encode_position, encode_side_information,
    build_m_d, build_m_t, build_m_zero, build_m_perm,
    canonical_budget_order, mean_five_seed_root_nll,
    compute_aulc, full_bootstrap_procedure, classify_outcome, CanonicalTensorF32
)
from .ml_runtime import configure_runtime, initialize_model_cpu_then_mps, build_frozen_adam

BOUND_FILES = [
    "src/chessheat/cp_representation_efficiency.py",
    "scripts/run_cp_representation_efficiency.py",
    "src/chessheat/protocol_freeze.py",
    "src/chessheat/ml_runtime.py",
    "artifacts/research/cp_representation_efficiency_protocol_v7.json",
    "artifacts/research/ml_runtime_pin_v3.json",
    "artifacts/research/ml_runtime_package_lock_v3.json",
    "artifacts/research/ml_runtime_code_lock_v3.json",
    "requirements/ml-runtime-v3.txt",
    "artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v2.json",
    "artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v7_rep1.json",
    "artifacts/research/target_label_derivation_runtime_pin_v1.json",
    "requirements/target-label-runtime-v1.txt"
]


def verify_approved_sha_gate(approved_sha: str, repo_root: str = "."):
    import os, re, subprocess
    if os.environ.get("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA") != approved_sha:
        raise ValueError("Missing or mismatched CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA")
    if not isinstance(approved_sha, str) or not re.match(r"^[0-9a-f]{40}$", approved_sha):
        raise ValueError("SHA must be exactly 40 lowercase hexadecimal characters.")
    try:
        # Check that there are no uncommitted changes in tracked files
        # AND reject index-only drift
        subprocess.check_call(["git", "diff", "--quiet"], cwd=repo_root)
        subprocess.check_call(["git", "diff", "--cached", "--quiet"], cwd=repo_root)
    except subprocess.CalledProcessError:
        raise ValueError("Dirty working tree or index-only drift detected.")
        
    try:
        typ = subprocess.check_output(["git", "cat-file", "-t", approved_sha], cwd=repo_root, stderr=subprocess.STDOUT).decode().strip()
        if typ != "commit":
            raise ValueError(f"Approved SHA must be a commit, got {typ}")
    except subprocess.CalledProcessError:
        raise ValueError("Nonexistent SHA.")
        
    try:
        subprocess.check_output(["git", "merge-base", "--is-ancestor", approved_sha, "HEAD"], cwd=repo_root, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        raise ValueError("Approved SHA is not an ancestor of HEAD.")
        
    for file_path in BOUND_FILES:
        try:
            commit_content = subprocess.check_output(["git", "show", f"{approved_sha}:{file_path}"], cwd=repo_root, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            raise ValueError(f"File {file_path} not found in commit {approved_sha}")
            
        with open(os.path.join(repo_root, file_path), "rb") as f:
            working_content = f.read()
            
        if commit_content != working_content:
            raise ValueError(f"Byte-for-byte mismatch in bound file {file_path}")

def check_real_training_authorization():
    if os.environ.get("CHESSHEAT_REAL_TRAINING_AUTHORIZED") != "CHESSHEAT_REAL_TRAINING_V1_AUTHORIZED":
        raise ValueError("Real training not authorized")

def check_analysis_authorization():
    if os.environ.get("CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED") != "CHESSHEAT_SCIENTIFIC_ANALYSIS_V1_AUTHORIZED":
        raise ValueError("Scientific analysis not authorized")

def _build_model(torch):
    nn = torch.nn
    class RepNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.spatial = nn.Sequential(
                nn.Conv2d(19, 64, kernel_size=3, stride=1, padding=1, bias=True),
                nn.ReLU(),
                nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1, bias=True),
                nn.ReLU(),
                nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1, bias=True),
                nn.ReLU(),
                nn.AdaptiveAvgPool2d((1, 1)),
                nn.Flatten()
            )
            self.side = nn.Sequential(
                nn.Linear(270, 128, bias=True),
                nn.ReLU()
            )
            self.combined = nn.Sequential(
                nn.Linear(192, 128, bias=True),
                nn.ReLU(),
                nn.Linear(128, 3, bias=True)
            )
            
        def forward(self, x_spatial, x_side):
            s = self.spatial(x_spatial)
            c = self.side(x_side)
            return self.combined(torch.cat([s, c], dim=1))
    return RepNet()

def get_epoch_order(seed: int, epoch: int, root_ids: List[str]) -> List[str]:
    def sort_key(rid: str):
        digest = hashlib.sha256(f"CHESSHEAT_MINIBATCH_V3|{seed}|{epoch}|{rid}".encode("utf-8")).hexdigest()
        return (digest, rid)
    return sorted(root_ids, key=sort_key)

def get_canonical_state_digest(model) -> str:
    sd = model.state_dict()
    h = hashlib.sha256()
    h.update(b"CHESSHEAT_MODEL_STATE_V2\n")
    for k in sorted(sd.keys()):
        t = sd[k].cpu().contiguous()
        name_b = len(k).to_bytes(4, 'little') + k.encode("utf-8")
        dtype_b = str(t.dtype).encode("utf-8")
        shape_b = str(list(t.shape)).encode("utf-8")
        h.update(name_b + b"\n" + dtype_b + b"\n" + shape_b + b"\n")
        h.update(bytes(t.untyped_storage().tolist()))
    return h.hexdigest()

@dataclass(frozen=True)
class LearnerRecord:
    p_tensor: Any
    side_tensor: Any
    spatial_map: Any
    label: int

class DerivedCache:
    def __init__(self, filepath: str = None, expected_sha: str = None):
        self.filepath = filepath
        self.roots = {}
        if filepath:
            self._build_index(expected_sha)
            
    def _build_index(self, expected_sha: str):
        import json
        import hashlib
        hasher = hashlib.sha256()
        with open(self.filepath, "rb") as f:
            offset = 0
            for line in f:
                hasher.update(line)
                length = len(line)
                rec = json.loads(line)
                rid = rec["root_identity"]
                if rid in self.roots:
                    raise ValueError("Duplicate root_identity")
                
                if offset < 0 or length <= 0:
                    raise ValueError("invalid offset or length")
                    
                self.roots[rid] = {
                    "root_identity": rid,
                    "byte_offset": offset,
                    "byte_length": length,
                    "partition": rec.get("partition"),
                    "source_pair_count": rec.get("source_pair_count", 0),
                    "target_evaluable_pair_count": rec.get("target_evaluable_pair_count", 0)
                }
                offset += length
            
            if offset > f.tell():
                raise ValueError("overlap or overrun")
        
        if expected_sha and hasher.hexdigest() != expected_sha:
            raise ValueError(f"Cache SHA mismatch, got {hasher.hexdigest()}")
                
    def get_root(self, rid: str) -> Dict:
        import json
        info = self.roots.get(rid)
        if not info:
            return None
        with open(self.filepath, "rb") as f:
            f.seek(info["byte_offset"])
            bytes_data = f.read(info["byte_length"])
            rec = json.loads(bytes_data)
            if rec["root_identity"] != rid:
                raise ValueError("Cache index mismatch")
            if rec["partition"] != info["partition"]:
                raise ValueError("partition mismatch")
            if rec.get("source_pair_count", 0) != info["source_pair_count"]:
                raise ValueError("source_pair_count mismatch")
            if rec.get("target_evaluable_pair_count", 0) != info["target_evaluable_pair_count"]:
                raise ValueError("target_evaluable_pair_count mismatch")
            return rec
def construct_learner_records(root_record: Dict, condition: str) -> List[LearnerRecord]:
    if root_record["schema"] != "CP_TARGET_PAIR_LABEL_ROOT_V6": raise ValueError("schema")
    if root_record["protocol_id"] != "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7": raise ValueError("protocol_id")
    if root_record["partition"] not in {"TRAIN", "VALIDATION", "TEST"}: raise ValueError("partition")
    rid = root_record.get("root_identity")
    if not rid: raise ValueError("root_identity")
    pairs = root_record["pairs"]
    if len(pairs) != root_record["source_pair_count"]: raise ValueError("pair count")
    
    eval_count = sum(1 for p in pairs if p.get("target_label") is not None)
    if eval_count != root_record["target_evaluable_pair_count"]: raise ValueError("Eval count mismatch")
    
    p = encode_position(root_record["sufficient_position"])
    records = []
    for pair in pairs:
        m1, m2 = pair["m1_uci"], pair["m2_uci"]
        if m1 >= m2: raise ValueError("m1_uci must be strictly less than m2_uci")
        
        expected_pair_id = hashlib.sha256(f"CHESSHEAT_TARGET_PAIR_V1|{rid}|{m1}|{m2}".encode('utf-8')).hexdigest()
        if str(pair["pair_id"]) != expected_pair_id: raise ValueError("Invalid pair_id")
        
        if pair.get("target_label") is None:
            if pair.get("target_non_evaluable_reason") != "TARGET_ACQUISITION_FAILURE":
                raise ValueError("Null target label requires target_non_evaluable_reason=TARGET_ACQUISITION_FAILURE")
            continue
            
        pf = SourcePairFeatures(pair["m1_uci"], pair["source_cp_m1"], 
                                pair["m2_uci"], pair["source_cp_m2"])
                                
        if "d_X" in pair and pair["d_X"] != pf.d_x:
            raise ValueError("d_X consistency failed")
        if "a_X" in pair and pair["a_X"] != pf.a_x:
            raise ValueError("a_X consistency failed")
            
        side = encode_side_information(pf)
        
        if condition == "mu_D":
            m = build_m_d(pf)
        elif condition == "mu_T":
            m = build_m_t(pf)
        elif condition == "B_daS":
            m = build_m_zero()
        elif condition == "B_perm":
            m = build_m_perm(pf)
        else:
            raise ValueError(f"Unknown condition {condition}")
            
        label = {"FIRST_BETTER": 0, "EQUAL": 1, "SECOND_BETTER": 2}[pair["target_label"]]
        records.append(LearnerRecord(p, side, m, label))
    return records

def read_and_validate_roots(records: List[Dict]) -> List[Dict]:
    seen_roots = set()
    for p in records:
        if p.get("schema") != "CP_TARGET_PAIR_LABEL_ROOT_V6":
            raise ValueError("Exact schema mismatch")
        if p.get("label_derivation_protocol") != "CP_TARGET_LABEL_DERIVATION_V6":
            raise ValueError("Exact label_derivation_protocol mismatch")
        if p.get("protocol_id") != "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7":
            raise ValueError("Exact protocol_id mismatch")
        if p.get("partition") not in {"TRAIN", "VALIDATION", "TEST"}:
            raise ValueError("Exact partition mismatch")
            
        rid = p.get("root_identity")
        if not rid: raise ValueError("missing root_identity")
        if rid in seen_roots:
            raise ValueError("Duplicate root_identity in population")
        seen_roots.add(rid)

        sp = p.get("sufficient_position", {})
        if sp.get("side_to_move") not in {"w", "b"}:
            raise ValueError("side_to_move must be w or b")

        eval_c = p.get("target_evaluable_pair_count", 0)
        noneval_c = p.get("target_non_evaluable_pair_count", 0)
        src_c = p.get("source_pair_count", 0)

        pairs = p.get("pairs", [])
        if len(pairs) != src_c:
            raise ValueError("len(pairs) != source_pair_count")

        actual_evaluable = sum(1 for pair in pairs if pair.get("target_label") is not None)
        actual_non_evaluable = sum(1 for pair in pairs if pair.get("target_label") is None)
        
        if actual_evaluable != eval_c:
            raise ValueError("actual_evaluable != target_evaluable_pair_count")
        if actual_non_evaluable != noneval_c:
            raise ValueError("actual_non_evaluable != target_non_evaluable_pair_count")
        if actual_evaluable + actual_non_evaluable != src_c:
            raise ValueError("actual_evaluable + actual_non_evaluable != source_pair_count")

        prev_m = None
        for pair in pairs:
            m1 = pair.get("m1_uci")
            m2 = pair.get("m2_uci")
            if not m1 or not m2: raise ValueError("Missing uci")
            if not (m1 < m2):
                raise ValueError("m1 must be less than m2")
            if prev_m is not None:
                if not (prev_m < (m1, m2)):
                    raise ValueError("pairs must be strictly lexically ordered by (m1, m2)")
            prev_m = (m1, m2)

            import hashlib
            expected_sha = hashlib.sha256(f"CHESSHEAT_TARGET_PAIR_V1|{rid}|{m1}|{m2}".encode()).hexdigest()
            if pair.get("pair_id") != expected_sha:
                raise ValueError("pair_id SHA mismatch")

            cp1 = pair.get("source_cp_m1")
            cp2 = pair.get("source_cp_m2")
            if type(cp1) is not int or type(cp2) is not int:
                raise ValueError("source cp must be int")

            from chessheat.cp_target_labels import SourcePairFeatures
            try:
                sf = SourcePairFeatures(m1, cp1, m2, cp2)
            except Exception:
                raise ValueError("bad cp values")
                
            if pair.get("d_X") != sf.d_x or pair.get("a_X") != sf.a_x:
                raise ValueError("a_x or d_x mismatch")
            
            tl = pair.get("target_label")
            if tl not in {"FIRST_BETTER", "EQUAL", "SECOND_BETTER", None}:
                raise ValueError("Invalid target label")
            if tl is None and pair.get("target_non_evaluable_reason") != "TARGET_ACQUISITION_FAILURE":
                raise ValueError("missing reason or invalid reason")
            if tl is not None and "target_non_evaluable_reason" in pair:
                raise ValueError("reason present with valid label")

    return records


def build_root_tensors(torch, records: List[LearnerRecord], device):
    if not records:
        return None
    spatial_list = []
    side_list = []
    labels = []
    for r in records:
        p_t = torch.tensor(r.p_tensor.values, dtype=torch.float32).view(18, 8, 8)
        m_t = torch.tensor(r.spatial_map.values, dtype=torch.float32).view(1, 8, 8)
        spatial = torch.cat([p_t, m_t], dim=0)
        spatial_list.append(spatial)
        
        side_t = torch.tensor(r.side_tensor.values, dtype=torch.float32)
        side_list.append(side_t)
        labels.append(r.label)
        
    x_spatial = torch.stack(spatial_list).to(device)
    x_side = torch.stack(side_list).to(device)
    y = torch.tensor(labels, dtype=torch.long).to(device)
    return x_spatial, x_side, y

def evaluate_roots(model, root_records_tensors: Any, root_ids: List[str], torch):
    model.eval()
    root_nlls = {}
    loss_fn = torch.nn.CrossEntropyLoss(reduction='none')
    is_callable = callable(root_records_tensors)
    with torch.no_grad():
        for rid in root_ids:
            if is_callable:
                tensors = root_records_tensors(rid)
            else:
                if rid not in root_records_tensors:
                    continue
                tensors = root_records_tensors[rid]
            if tensors is None:
                continue
            x_spatial, x_side, y = tensors
            logits = model(x_spatial, x_side)
            loss = loss_fn(logits, y).mean()
            root_nlls[rid] = loss.item()
            del x_spatial, x_side, y, logits, loss
    return root_nlls

def run_training_job(
    condition: str,
    nominal_budget: int,
    seed: int,
    training_root_records: Optional[List[Dict]] = None,
    validation_root_records: Optional[List[Dict]] = None,
    test_root_records: Optional[List[Dict]] = None,
    nominal_root_population_digest: Optional[str] = None,
    validation_population_digest: Optional[str] = None,
    test_population_digest: Optional[str] = None,
    cache: Optional[Any] = None,
    nominal_root_ids: Optional[Tuple[str, ...]] = None,
    validation_root_ids: Optional[Tuple[str, ...]] = None,
    test_root_ids: Optional[Tuple[str, ...]] = None,
):
    if condition == "B_raw":
        raise ValueError("B_RAW_NOT_EXECUTED_IN_PRIMARY_V2_PIPELINE")
        
    valid_budgets = {250, 500, 1000, 2000, 4000, 8000, 16000, 20000}
    if nominal_budget not in valid_budgets:
        raise ValueError("Invalid budget")
        
    ctx = configure_runtime(seed)
    torch = ctx.torch
    device = ctx.device
    
    model = initialize_model_cpu_then_mps(_build_model, ctx)
    optimizer = build_frozen_adam(model, torch)
    loss_fn = torch.nn.CrossEntropyLoss(reduction='none')
    
    if cache is not None:
        if nominal_root_ids is None or validation_root_ids is None or test_root_ids is None:
            raise ValueError("nominal_root_ids, validation_root_ids, and test_root_ids required when cache is provided")
        if len(nominal_root_ids) != nominal_budget:
            raise ValueError("Nominal root count mismatch")
            
        calculated_train_digest = canonical_root_population_digest(nominal_root_ids)
        if calculated_train_digest != nominal_root_population_digest:
            raise ValueError("Train population digest mismatch")
        
        calculated_val_digest = canonical_root_population_digest(validation_root_ids)
        if calculated_val_digest != validation_population_digest:
            raise ValueError("Validation population digest mismatch")
            
        calculated_test_digest = canonical_root_population_digest(test_root_ids)
        if calculated_test_digest != test_population_digest:
            raise ValueError("Test population digest mismatch")
            
        if hasattr(cache, "roots") and cache.roots:
            effective_root_ids = [rid for rid in nominal_root_ids if cache.roots[rid].get("target_evaluable_pair_count", 0) > 0]
        else:
            effective_root_ids = []
            for rid in nominal_root_ids:
                rec = cache.get_root(rid)
                if rec and (rec.get("target_evaluable_pair_count", 0) > 0 or any(p.get("target_label") is not None for p in rec.get("pairs", []))):
                    effective_root_ids.append(rid)
                    
        for rid in validation_root_ids:
            if hasattr(cache, "roots") and cache.roots:
                if cache.roots[rid].get("target_evaluable_pair_count", 0) < 1:
                    raise ValueError("Fail if 0-evaluable roots in val/test")
            else:
                rec = cache.get_root(rid)
                if not rec or (rec.get("target_evaluable_pair_count", 0) < 1 and not any(p.get("target_label") is not None for p in rec.get("pairs", []))):
                    raise ValueError("Fail if 0-evaluable roots in val/test")
                    
        for rid in test_root_ids:
            if hasattr(cache, "roots") and cache.roots:
                if cache.roots[rid].get("target_evaluable_pair_count", 0) < 1:
                    raise ValueError("Fail if 0-evaluable roots in val/test")
            else:
                rec = cache.get_root(rid)
                if not rec or (rec.get("target_evaluable_pair_count", 0) < 1 and not any(p.get("target_label") is not None for p in rec.get("pairs", []))):
                    raise ValueError("Fail if 0-evaluable roots in val/test")
                    
        def loader(rid: str):
            rec = cache.get_root(rid)
            if not rec:
                raise ValueError(f"Root {rid} not found in cache")
            read_and_validate_roots([rec])
            recs = construct_learner_records(rec, condition)
            if not recs:
                return None
            return build_root_tensors(torch, recs, device)
            
        nom_root_ids = nominal_root_ids
        val_root_ids = validation_root_ids
        tst_root_ids = test_root_ids
        
    elif training_root_records is not None:
        if len(training_root_records) != nominal_budget:
            raise ValueError("Nominal root count mismatch")
            
        sorted_recs = sorted(training_root_records, key=lambda x: canonical_budget_order(x["root_identity"]))
        if [r["root_identity"] for r in training_root_records] != [r["root_identity"] for r in sorted_recs][:nominal_budget]:
            raise ValueError("Invalid training roots prefix")
            
        calculated_train_digest = canonical_root_population_digest([r["root_identity"] for r in training_root_records])
        if calculated_train_digest != nominal_root_population_digest:
            raise ValueError("Train population digest mismatch")
        
        calculated_val_digest = canonical_root_population_digest([r["root_identity"] for r in validation_root_records])
        if calculated_val_digest != validation_population_digest:
            raise ValueError("Validation population digest mismatch")
            
        calculated_test_digest = canonical_root_population_digest([r["root_identity"] for r in test_root_records])
        if calculated_test_digest != test_population_digest:
            raise ValueError("Test population digest mismatch")
            
        records_map = {r["root_identity"]: r for r in training_root_records}
        for r in validation_root_records:
            records_map[r["root_identity"]] = r
        for r in test_root_records:
            records_map[r["root_identity"]] = r
            
        nom_root_ids = tuple(r["root_identity"] for r in training_root_records)
        val_root_ids = tuple(r["root_identity"] for r in validation_root_records)
        tst_root_ids = tuple(r["root_identity"] for r in test_root_records)
        
        effective_root_ids = [
            r["root_identity"] for r in training_root_records
            if r.get("target_evaluable_pair_count", sum(1 for p in r.get("pairs", []) if p.get("target_label") is not None)) > 0
        ]
        
        for r in validation_root_records:
            eval_c = r.get("target_evaluable_pair_count", sum(1 for p in r.get("pairs", []) if p.get("target_label") is not None))
            if eval_c < 1:
                raise ValueError("Fail if 0-evaluable roots in val/test")
                
        for r in test_root_records:
            eval_c = r.get("target_evaluable_pair_count", sum(1 for p in r.get("pairs", []) if p.get("target_label") is not None))
            if eval_c < 1:
                raise ValueError("Fail if 0-evaluable roots in val/test")
                
        def loader(rid: str):
            rec = records_map.get(rid)
            if not rec:
                raise ValueError(f"Root {rid} not found")
            read_and_validate_roots([rec])
            recs = construct_learner_records(rec, condition)
            if not recs:
                return None
            return build_root_tensors(torch, recs, device)
    else:
        raise ValueError("Either cache or training_root_records must be provided")

    if not val_root_ids:
        raise ValueError("Validation population cannot be empty.")
        
    best_val_nll = float('inf')
    best_epoch = -1
    best_state_digest = None
    best_state_dict = None
    patience = 20
    non_improvement = 0
    val_trace = []
    
    effective_root_population_digest = canonical_root_population_digest(effective_root_ids)
    test_eval_count = 0
    
    for epoch in range(200):
        model.train()
        epoch_root_ids = get_epoch_order(seed, epoch, effective_root_ids)
        
        for i in range(0, len(epoch_root_ids), 64):
            batch_rids = epoch_root_ids[i:i+64]
            optimizer.zero_grad()
            B = len(batch_rids)
            total_loss = 0
            for rid in batch_rids:
                tensors = loader(rid)
                if tensors is None:
                    continue
                x_spatial, x_side, y = tensors
                logits = model(x_spatial, x_side)
                root_loss = loss_fn(logits, y).mean()
                total_loss += root_loss
                del tensors, x_spatial, x_side, y, logits, root_loss
            if B > 0:
                (total_loss / B).backward()
                optimizer.step()
            del total_loss
            
        val_nlls = evaluate_roots(model, loader, list(val_root_ids), torch)
        val_loss = sum(val_nlls.values()) / len(val_nlls)
        if not math.isfinite(val_loss):
            raise ValueError("Non-finite validation loss encountered")
            
        val_trace.append(val_loss)
        
        if val_loss < best_val_nll:
            best_val_nll = val_loss
            best_epoch = epoch
            non_improvement = 0
            best_state_dict = copy.deepcopy(model.state_dict())
            best_state_digest = get_canonical_state_digest(model)
        else:
            non_improvement += 1
            
        if non_improvement >= patience:
            break
            
    model.load_state_dict(best_state_dict)
    
    test_nlls = evaluate_roots(model, loader, list(tst_root_ids), torch)
    test_eval_count += 1
    
    return {
        "schema": "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V14",
        "condition": condition,
        "nominal_budget": nominal_budget,
        "seed": seed,
        "nominal_root_count": len(nom_root_ids),
        "nominal_root_population_digest": nominal_root_population_digest,
        "effective_training_root_count": len(effective_root_ids),
        "effective_root_population_digest": effective_root_population_digest,
        "validation_population_digest": validation_population_digest,
        "test_population_digest": test_population_digest,
        "best_epoch": best_epoch,
        "best_validation_root_nll": best_val_nll,
        "epochs_completed": epoch + 1,
        "validation_trace": val_trace,
        "test_evaluation_count": test_eval_count,
        "test_root_ids": tuple(tst_root_ids),
        "test_root_losses": test_nlls,
        "canonical_model_state_sha": best_state_digest
    }

def run_scientific_analysis(worker_results: List[Dict]):
    check_analysis_authorization()
    
    aggregated_data = {}
    for res in worker_results:
        c = res["condition"]
        if c == "B_perm" or c == "B_raw":
            continue
            
        b = res["nominal_budget"]
        s = res["seed"]
        nlls = res["test_root_losses"]
        
        if c not in aggregated_data:
            aggregated_data[c] = {}
        if b not in aggregated_data[c]:
            aggregated_data[c][b] = {}
        aggregated_data[c][b][s] = nlls
        
    mean_nlls = {}
    for c, budgets in aggregated_data.items():
        mean_nlls[c] = {}
        for b, seeds_data in budgets.items():
            if len(seeds_data) != 5:
                raise ValueError(f"Expected 5 seeds for condition {c}, budget {b}, got {len(seeds_data)}")
                
            mean_nlls[c][b] = {}
            test_roots = list(seeds_data.values())[0].keys()
            for root in test_roots:
                root_seed_nlls = {seed: nlls[root] for seed, nlls in seeds_data.items()}
                mean_nlls[c][b][root] = mean_five_seed_root_nll(root_seed_nlls)
                
    utilities = {}
    for c, budgets in mean_nlls.items():
        utilities[c] = {}
        for b, root_nlls in budgets.items():
            avg_test_nll = sum(root_nlls.values()) / len(root_nlls)
            utilities[c][b] = -avg_test_nll
            
    budgets_ordered = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    aulcs = {}
    for c, u in utilities.items():
        utils_ordered = [u[b] for b in budgets_ordered]
        aulcs[c] = compute_aulc(budgets_ordered, utils_ordered)
        
    test_root_ids = list(mean_nlls["mu_D"][250].keys())
    ci_results = full_bootstrap_procedure(test_root_ids, mean_nlls)
    
    dt_ci = (ci_results["Delta_DT"]["lcb"], ci_results["Delta_DT"]["ucb"])
    d0_ci = (ci_results["Delta_D0"]["lcb"], ci_results["Delta_D0"]["ucb"])
    t0_ci = (ci_results["Delta_T0"]["lcb"], ci_results["Delta_T0"]["ucb"])
    
    outcome = classify_outcome(dt_ci, d0_ci, t0_ci, True)
    
    return {
        "AULC_D": aulcs.get("mu_D"),
        "AULC_T": aulcs.get("mu_T"),
        "AULC_BdaS": aulcs.get("B_daS"),
        "outcome": outcome,
        "ci_results": ci_results
    }

import hashlib
from typing import Dict, List

@dataclass(frozen=True)
class EvidenceIdentity:
    protocol_v7_sha: str
    seal_v2_sha: Optional[str]
    runtime_v3_pin_sha: str
    runtime_v3_package_lock_sha: str
    runtime_v3_code_lock_sha: str
    runtime_v3_requirements_sha: str
    target_label_runtime_pin_sha: str
    target_label_requirements_sha: str
    evidence_audit_commit: str
    evidence_supplement_commit: str
    label_scientific_sha: str
    label_compressed_sha: str
    lineage: str = "V6_HISTORICAL"
    replication_seal_sha: Optional[str] = None
    source_raw_sha: Optional[str] = None
    target_raw_sha: Optional[str] = None
    manifest_digest: Optional[str] = None
    derivation_implementation_commit: Optional[str] = None

def verify_training_evidence_preflight(approved_implementation_sha: str, repo_root: str = ".") -> EvidenceIdentity:
    import os
    import subprocess
    def get_sha(path):
        import hashlib
        with open(os.path.join(repo_root, path), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
            
    if get_sha("artifacts/research/cp_representation_efficiency_protocol_v7.json") != "ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef":
        raise ValueError("SHA mismatch for artifacts/research/cp_representation_efficiency_protocol_v7.json")
    if get_sha("artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v2.json") != "2e4735f40124f4eb7017ff816a4ea55e9f72ac559236a6077a0104273b1ab9c4":
        raise ValueError("SHA mismatch for artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v2.json")
    if get_sha("artifacts/research/ml_runtime_pin_v3.json") != "e69ae6bcbf96a327b021665b5ac21b63c269cd821be84d567867058b09e98932":
        raise ValueError("SHA mismatch for artifacts/research/ml_runtime_pin_v3.json")
    if get_sha("artifacts/research/ml_runtime_package_lock_v3.json") != "2127b9709ef8786f47b9306040a56706ff3a7f6535d2439d692c67bac5fac54d":
        raise ValueError("SHA mismatch for artifacts/research/ml_runtime_package_lock_v3.json")
    if get_sha("artifacts/research/ml_runtime_code_lock_v3.json") != "9eebefd15c6c1fe93340a69f270f9bf02f7572b4a307d174307f786355a4ec84":
        raise ValueError("SHA mismatch for artifacts/research/ml_runtime_code_lock_v3.json")
    if get_sha("requirements/ml-runtime-v3.txt") != "79ea33529376312052c7f98d0e19e812029697d4ff15a2e93106f94f023bf7c9":
        raise ValueError("SHA mismatch for requirements/ml-runtime-v3.txt")
    if get_sha("artifacts/research/target_label_derivation_runtime_pin_v1.json") != "dc707aa6d2709fcdfb108263356a8b0cab4cc459dffd29ba5524241f48ea3e22":
        raise ValueError("SHA mismatch for artifacts/research/target_label_derivation_runtime_pin_v1.json")
    if get_sha("requirements/target-label-runtime-v1.txt") != "da56c02977e00d88d897af40d227d773822aa7134d30e1d40c68e1518d666026":
        raise ValueError("SHA mismatch for requirements/target-label-runtime-v1.txt")

    try:
        subprocess.check_call(["git", "merge-base", "--is-ancestor", "2f7560a38427754404c6f1ee6115db950d18815c", approved_implementation_sha], cwd=repo_root, stderr=subprocess.STDOUT)
    except Exception:
        raise ValueError("evidence audit commit missing or not ancestor")
        
    try:
        subprocess.check_call(["git", "merge-base", "--is-ancestor", "87e1edad72d2899d0bc7a05d11d9601d60b7cba3", approved_implementation_sha], cwd=repo_root, stderr=subprocess.STDOUT)
    except Exception:
        raise ValueError("evidence supplement commit missing or not ancestor")

    return EvidenceIdentity(
        protocol_v7_sha=get_sha("artifacts/research/cp_representation_efficiency_protocol_v7.json"),
        seal_v2_sha=get_sha("artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v2.json"),
        runtime_v3_pin_sha=get_sha("artifacts/research/ml_runtime_pin_v3.json"),
        runtime_v3_package_lock_sha=get_sha("artifacts/research/ml_runtime_package_lock_v3.json"),
        runtime_v3_code_lock_sha=get_sha("artifacts/research/ml_runtime_code_lock_v3.json"),
        runtime_v3_requirements_sha=get_sha("requirements/ml-runtime-v3.txt"),
        target_label_runtime_pin_sha=get_sha("artifacts/research/target_label_derivation_runtime_pin_v1.json"),
        target_label_requirements_sha=get_sha("requirements/target-label-runtime-v1.txt"),
        evidence_audit_commit="2f7560a38427754404c6f1ee6115db950d18815c",
        evidence_supplement_commit="87e1edad72d2899d0bc7a05d11d9601d60b7cba3",
        label_scientific_sha="c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2",
        label_compressed_sha="dea9346f9cb125f9c35e8824bb937daf4ea7fc51cff7f6c7c437caac8ae2c92d",
        lineage="V6_HISTORICAL"
    )

def verify_replication_training_evidence_preflight(approved_implementation_sha: str, repo_root: str = ".") -> EvidenceIdentity:
    import os
    import json
    import subprocess
    def get_sha(path):
        import hashlib
        with open(os.path.join(repo_root, path), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
            
    if get_sha("artifacts/research/cp_representation_efficiency_protocol_v7.json") != "ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef":
        raise ValueError("SHA mismatch for artifacts/research/cp_representation_efficiency_protocol_v7.json")
    seal_rel = "artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v7_rep1.json"
    seal_sha = get_sha(seal_rel)
    if seal_sha != "c2457bb1531856b0e2b235a69dd2b7b77b64e2419032cf6616cffe6a96b2baa8":
        raise ValueError(f"SHA mismatch for {seal_rel}: got {seal_sha}")
    if get_sha("artifacts/research/ml_runtime_pin_v3.json") != "e69ae6bcbf96a327b021665b5ac21b63c269cd821be84d567867058b09e98932":
        raise ValueError("SHA mismatch for artifacts/research/ml_runtime_pin_v3.json")
    if get_sha("artifacts/research/ml_runtime_package_lock_v3.json") != "2127b9709ef8786f47b9306040a56706ff3a7f6535d2439d692c67bac5fac54d":
        raise ValueError("SHA mismatch for artifacts/research/ml_runtime_package_lock_v3.json")
    if get_sha("artifacts/research/ml_runtime_code_lock_v3.json") != "9eebefd15c6c1fe93340a69f270f9bf02f7572b4a307d174307f786355a4ec84":
        raise ValueError("SHA mismatch for artifacts/research/ml_runtime_code_lock_v3.json")
    if get_sha("requirements/ml-runtime-v3.txt") != "79ea33529376312052c7f98d0e19e812029697d4ff15a2e93106f94f023bf7c9":
        raise ValueError("SHA mismatch for requirements/ml-runtime-v3.txt")
    if get_sha("artifacts/research/target_label_derivation_runtime_pin_v1.json") != "dc707aa6d2709fcdfb108263356a8b0cab4cc459dffd29ba5524241f48ea3e22":
        raise ValueError("SHA mismatch for artifacts/research/target_label_derivation_runtime_pin_v1.json")
    if get_sha("requirements/target-label-runtime-v1.txt") != "da56c02977e00d88d897af40d227d773822aa7134d30e1d40c68e1518d666026":
        raise ValueError("SHA mismatch for requirements/target-label-runtime-v1.txt")

    seal_full_path = os.path.join(repo_root, seal_rel)
    with open(seal_full_path, "r", encoding="utf-8") as f:
        seal_data = json.load(f)

    if seal_data.get("schema") != "CP_TARGET_LABEL_DERIVATION_SEAL_V7_REP1":
        raise ValueError("Invalid schema in replication seal")
    if seal_data.get("status") != "TARGET_LABEL_DERIVATION_V7_REP1_SEALED":
        raise ValueError("Invalid status in replication seal")
    if seal_data.get("protocol_id") != "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7":
        raise ValueError("protocol_id mismatch in replication seal")
    if seal_data.get("label_derivation_protocol") != "CP_TARGET_LABEL_DERIVATION_V7_REPLICATION_1":
        raise ValueError("label_derivation_protocol mismatch in replication seal")
    if seal_data.get("protocol_json_sha256") != "ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef":
        raise ValueError("protocol_json_sha256 mismatch in replication seal")
    if seal_data.get("source_raw_sha256") != "9cfe28a13f185e207ac42c5708597b0577ef93f4fce29ca482e4e6a9c8d83774":
        raise ValueError("source_raw_sha256 mismatch in replication seal")
    if seal_data.get("target_raw_sha256") != "d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00":
        raise ValueError("target_raw_sha256 mismatch in replication seal")
    if seal_data.get("manifest_decompressed_sha256") != "5a013e64265820b65d1d3687fcee98aa607ab41470294d11df7b2f803c8e063d":
        raise ValueError("manifest_decompressed_sha256 mismatch in replication seal")
    if seal_data.get("decompressed_canonical_sha256") != "1b148d07c1cad975b5d21233cd7b384493a61a666cdec06b4e733b82379afba3":
        raise ValueError("decompressed_canonical_sha256 mismatch in replication seal")
    if seal_data.get("compressed_sha256") != "5ab9d94e5806b19721879962f15e5ecd1763cdb0380c85337571af6596a3a61e":
        raise ValueError("compressed_sha256 mismatch in replication seal")
    if seal_data.get("implementation_sha") != "14b85055fd439cf7f905adf51718544485b1ac17":
        raise ValueError("implementation_sha mismatch in replication seal")
    if seal_data.get("pair_eligible_root_count") != 33444:
        raise ValueError("pair_eligible_root_count mismatch in replication seal")
    if seal_data.get("source_pair_count") != 17788903:
        raise ValueError("source_pair_count mismatch in replication seal")

    raw_source_path = os.path.join(repo_root, "artifacts/research/cp_source_feasibility_2026_07/raw/cp_source_root_results_v2.jsonl")
    if os.path.exists(raw_source_path):
        if get_sha("artifacts/research/cp_source_feasibility_2026_07/raw/cp_source_root_results_v2.jsonl") != "9cfe28a13f185e207ac42c5708597b0577ef93f4fce29ca482e4e6a9c8d83774":
            raise ValueError("SHA mismatch for raw source artifact")

    raw_target_path = os.path.join(repo_root, "artifacts/research/cp_target_acquisition_2026_07/raw/cp_target_root_results_v2.jsonl")
    if os.path.exists(raw_target_path):
        if get_sha("artifacts/research/cp_target_acquisition_2026_07/raw/cp_target_root_results_v2.jsonl") != "d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00":
            raise ValueError("SHA mismatch for raw target artifact")

    for commit_sha in [
        "14b85055fd439cf7f905adf51718544485b1ac17",
        "732ba450f47511d0f93af0dcaef924b2f2a57f89",
        "2f7560a38427754404c6f1ee6115db950d18815c",
        "87e1edad72d2899d0bc7a05d11d9601d60b7cba3"
    ]:
        try:
            subprocess.check_call(["git", "merge-base", "--is-ancestor", commit_sha, approved_implementation_sha], cwd=repo_root, stderr=subprocess.STDOUT)
        except Exception:
            raise ValueError(f"Required provenance commit {commit_sha} missing or not an ancestor of {approved_implementation_sha}")

    return EvidenceIdentity(
        protocol_v7_sha=get_sha("artifacts/research/cp_representation_efficiency_protocol_v7.json"),
        seal_v2_sha=None,
        runtime_v3_pin_sha=get_sha("artifacts/research/ml_runtime_pin_v3.json"),
        runtime_v3_package_lock_sha=get_sha("artifacts/research/ml_runtime_package_lock_v3.json"),
        runtime_v3_code_lock_sha=get_sha("artifacts/research/ml_runtime_code_lock_v3.json"),
        runtime_v3_requirements_sha=get_sha("requirements/ml-runtime-v3.txt"),
        target_label_runtime_pin_sha=get_sha("artifacts/research/target_label_derivation_runtime_pin_v1.json"),
        target_label_requirements_sha=get_sha("requirements/target-label-runtime-v1.txt"),
        evidence_audit_commit="2f7560a38427754404c6f1ee6115db950d18815c",
        evidence_supplement_commit="87e1edad72d2899d0bc7a05d11d9601d60b7cba3",
        label_scientific_sha="1b148d07c1cad975b5d21233cd7b384493a61a666cdec06b4e733b82379afba3",
        label_compressed_sha="5ab9d94e5806b19721879962f15e5ecd1763cdb0380c85337571af6596a3a61e",
        lineage="V7_REPLICATION_1",
        replication_seal_sha=seal_sha,
        source_raw_sha="9cfe28a13f185e207ac42c5708597b0577ef93f4fce29ca482e4e6a9c8d83774",
        target_raw_sha="d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00",
        manifest_digest="5a013e64265820b65d1d3687fcee98aa607ab41470294d11df7b2f803c8e063d",
        derivation_implementation_commit="14b85055fd439cf7f905adf51718544485b1ac17"
    )

def canonical_root_population_digest(root_ids):
    import hashlib
    h = hashlib.sha256()
    h.update(b"CHESSHEAT_ROOT_POPULATION_V1\n")
    h.update(f"{len(root_ids):010d}\n".encode("utf-8"))
    for rid in root_ids:
        encoded = rid.encode("utf-8")
        h.update(f"{len(encoded):010d}\n".encode("utf-8"))
        h.update(encoded)
        h.update(b"\n")
    return h.hexdigest()


def build_frozen_populations(cache: DerivedCache):
    budgets = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    
    train_roots = []
    val_roots = []
    test_roots = []
    
    for rid, data in cache.roots.items():
        if data["partition"] == "TRAIN" and data.get("source_pair_count", 0) > 0:
            train_roots.append(rid)
        elif data.get("target_evaluable_pair_count", 0) >= 1:
            if data["partition"] == "VALIDATION":
                val_roots.append(rid)
            elif data["partition"] == "TEST":
                test_roots.append(rid)
                
    if len(train_roots) < 20000:
        raise ValueError("Insufficient eligible TRAIN universe")
        
    train_roots = sorted(train_roots, key=lambda rid: canonical_budget_order(rid))
    
    val_roots = tuple(sorted(val_roots))
    test_roots = tuple(sorted(test_roots))
    d_val = canonical_root_population_digest(val_roots)
    d_test = canonical_root_population_digest(test_roots)
    
    budget_digests = {}
    for b in budgets:
        budget_digests[b] = canonical_root_population_digest(train_roots[:b])
        
    return train_roots, budgets, val_roots, test_roots, d_val, d_test, budget_digests
from dataclasses import dataclass
@dataclass(frozen=True)
class JobSpec:
    condition: str
    nominal_budget: int
    seed: int
    nominal_root_ids: tuple
    nominal_root_population_digest: str
    validation_root_ids: tuple
    validation_population_digest: str
    test_root_ids: tuple
    test_population_digest: str
    protocol_v7_sha: str
    seal_v2_sha: Optional[str]
    label_scientific_sha: str
    runtime_v3_identity: str
    runtime_v3_pin_sha: str
    approved_implementation_sha: str
    cache_path: str
    effective_root_population_digest: Optional[str] = None
    lineage: str = "V6_HISTORICAL"
    replication_seal_sha: Optional[str] = None

def build_job_specs(populations, ev_id, cache_path, approved_sha):
    specs = []
    conditions = ["mu_D", "mu_T", "B_daS", "B_perm"]
    train_roots, budgets, val_roots, test_roots, d_val, d_test, budget_digests = populations
    # test_roots and val_roots should already be sorted lexically by build_frozen_populations
    for cond in conditions:
        for b in budgets:
            for s in [1729, 2718, 31415, 65537, 104729]:
                specs.append(JobSpec(
                    condition=cond,
                    nominal_budget=b,
                    seed=s,
                    nominal_root_ids=tuple(train_roots[:b]),
                    nominal_root_population_digest=budget_digests[b],
                    validation_root_ids=tuple(val_roots),
                    validation_population_digest=d_val,
                    test_root_ids=tuple(test_roots),
                    test_population_digest=d_test,
                    protocol_v7_sha=ev_id.protocol_v7_sha,
                    seal_v2_sha=ev_id.seal_v2_sha,
                    label_scientific_sha=ev_id.label_scientific_sha,
                    runtime_v3_identity="CHESSHEAT_ML_RUNTIME_V3",
                    runtime_v3_pin_sha=ev_id.runtime_v3_pin_sha,
                    approved_implementation_sha=approved_sha,
                    cache_path=cache_path,
                    lineage=getattr(ev_id, "lineage", "V6_HISTORICAL"),
                    replication_seal_sha=getattr(ev_id, "replication_seal_sha", None)
                ))
    if len(specs) != 160:
        raise ValueError("Must have exactly 160 specs")
    return specs
def _process_wrapper(spec, worker_fn, q):
    try:
        res = worker_fn(spec)
        q.put((True, res))
    except Exception as e:
        q.put((False, e))

def run_job_specs(
    job_specs: List[JobSpec],
    worker_fn,
    watchdog_timeout: float = 7200.0,
    on_result_success = None
):
    import multiprocessing
    import queue
    results = []
    
    for spec in job_specs:
        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=_process_wrapper, args=(spec, worker_fn, q))
        p.start()
        
        import time
        start_t = time.monotonic()
        res_tuple = None
        while True:
            try:
                res_tuple = q.get(timeout=1.0)
                break
            except queue.Empty:
                if not p.is_alive():
                    # check again to prevent race condition
                    try:
                        res_tuple = q.get_nowait()
                        break
                    except queue.Empty:
                        break
                
                if time.monotonic() - start_t > watchdog_timeout:
                    p.terminate()
                    p.join()
                    q.close()
                    raise RuntimeError("Worker watchdog timeout exceeded")
        
        p.join()
        
        if p.exitcode != 0:
            raise RuntimeError(f"Process crashed with exit code {p.exitcode}")
            
        if res_tuple is None:
            raise RuntimeError("Process died without returning a result")
            
        success, res = res_tuple
        if not success:
            raise res
            
        if on_result_success is not None:
            on_result_success(spec, res)
            
        results.append(res)
        
    return results


def run_downstream_worker(spec: JobSpec):
    cache = DerivedCache(spec.cache_path, spec.label_scientific_sha)
    
    if hasattr(cache, "roots") and cache.roots:
        for r in spec.nominal_root_ids:
            info = cache.roots.get(r)
            if not info: raise ValueError(f"Root {r} not found")
            if info.get("partition") != "TRAIN" or info.get("source_pair_count", 0) <= 0:
                raise ValueError(f"Root {r} invalid partition or zero source pairs in TRAIN")
                
        for r in spec.validation_root_ids:
            info = cache.roots.get(r)
            if not info: raise ValueError(f"Root {r} not found")
            if info.get("partition") != "VALIDATION" or info.get("target_evaluable_pair_count", 0) < 1:
                raise ValueError(f"Root {r} invalid partition or zero evaluable pairs in VALIDATION")
                
        for r in spec.test_root_ids:
            info = cache.roots.get(r)
            if not info: raise ValueError(f"Root {r} not found")
            if info.get("partition") != "TEST" or info.get("target_evaluable_pair_count", 0) < 1:
                raise ValueError(f"Root {r} invalid partition or zero evaluable pairs in TEST")
                
    if canonical_root_population_digest(spec.nominal_root_ids) != spec.nominal_root_population_digest:
        raise ValueError("Nominal digest mismatch in worker")
    if canonical_root_population_digest(spec.validation_root_ids) != spec.validation_population_digest:
        raise ValueError("Validation digest mismatch in worker")
    if canonical_root_population_digest(spec.test_root_ids) != spec.test_population_digest:
        raise ValueError("Test digest mismatch in worker")
        
    result = run_training_job(
        condition=spec.condition,
        nominal_budget=spec.nominal_budget,
        seed=spec.seed,
        cache=cache,
        nominal_root_ids=spec.nominal_root_ids,
        validation_root_ids=spec.validation_root_ids,
        test_root_ids=spec.test_root_ids,
        nominal_root_population_digest=spec.nominal_root_population_digest,
        validation_population_digest=spec.validation_population_digest,
        test_population_digest=spec.test_population_digest,
    )
    
    # Binding and Validating Result
    if result.get("schema") != "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V14":
        raise ValueError("Invalid schema returned by training job")
    if result.get("condition") != spec.condition: raise ValueError("Condition mismatch")
    if result.get("nominal_budget") != spec.nominal_budget: raise ValueError("Budget mismatch")
    if result.get("seed") != spec.seed: raise ValueError("Seed mismatch")
    
    if result.get("nominal_root_count") != len(spec.nominal_root_ids) or result.get("nominal_root_count") != spec.nominal_budget:
        raise ValueError("nominal_root_count mismatch")
        
    if not (0 <= result.get("effective_training_root_count", -1) <= result.get("nominal_root_count")):
        raise ValueError("effective_training_root_count bounds error")
        
    if result.get("test_evaluation_count") != 1:
        raise ValueError("test_evaluation_count != 1")
        
    if tuple(result.get("test_root_ids", ())) != tuple(spec.test_root_ids):
        raise ValueError("test_root_ids mismatch")
        
    if result.get("nominal_root_population_digest") != spec.nominal_root_population_digest:
        raise ValueError("Nominal population digest mismatch in training result")
    if result.get("validation_population_digest") != spec.validation_population_digest:
        raise ValueError("Validation population digest mismatch in training result")
    if result.get("test_population_digest") != spec.test_population_digest:
        raise ValueError("Test population digest mismatch in training result")
        
    result["approved_implementation_sha"] = spec.approved_implementation_sha
    result["protocol_v7_sha"] = spec.protocol_v7_sha
    result["seal_v2_sha"] = spec.seal_v2_sha
    result["replication_seal_sha"] = getattr(spec, "replication_seal_sha", None)
    result["lineage"] = getattr(spec, "lineage", "V6_HISTORICAL")
    result["label_scientific_sha"] = spec.label_scientific_sha
    result["runtime_v3_identity"] = spec.runtime_v3_identity
    result["runtime_v3_pin_sha"] = spec.runtime_v3_pin_sha
    
    validate_worker_result(spec, result)
    return result

def validate_worker_result(spec: JobSpec, res: Dict) -> Dict:
    if not isinstance(res, dict):
        raise ValueError("Worker result must be a dict")
        
    if res.get("schema") != "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V14":
        raise ValueError("Schema mismatch in worker result")
        
    if res.get("condition") != spec.condition:
        raise ValueError("condition mismatch")
    if res.get("nominal_budget") != spec.nominal_budget:
        raise ValueError("nominal_budget mismatch")
    if res.get("seed") != spec.seed:
        raise ValueError("seed mismatch")

    expected_lineage = getattr(spec, "lineage", "V6_HISTORICAL")
    res_lineage = res.get("lineage", "V6_HISTORICAL")
    if res_lineage != expected_lineage:
        raise ValueError(f"Worker result lineage mismatch: expected {expected_lineage}, got {res_lineage}")
        
    if res.get("approved_implementation_sha") != spec.approved_implementation_sha:
        raise ValueError("approved_implementation_sha mismatch")
    if res.get("protocol_v7_sha") != spec.protocol_v7_sha:
        raise ValueError("protocol_v7_sha mismatch")
    if res.get("seal_v2_sha") != spec.seal_v2_sha:
        raise ValueError("seal_v2_sha mismatch")
    if res.get("replication_seal_sha") != getattr(spec, "replication_seal_sha", None):
        raise ValueError("replication_seal_sha mismatch")
    if res.get("label_scientific_sha") != spec.label_scientific_sha:
        raise ValueError("label_scientific_sha mismatch")
    if res.get("runtime_v3_identity") != spec.runtime_v3_identity:
        raise ValueError("runtime_v3_identity mismatch")
    if res.get("runtime_v3_pin_sha") != spec.runtime_v3_pin_sha:
        raise ValueError("runtime_v3_pin_sha mismatch")
        
    if res.get("nominal_root_population_digest") != spec.nominal_root_population_digest:
        raise ValueError("nominal_root_population_digest mismatch")
    if res.get("validation_population_digest") != spec.validation_population_digest:
        raise ValueError("validation_population_digest mismatch")
    if res.get("test_population_digest") != spec.test_population_digest:
        raise ValueError("test_population_digest mismatch")
        
    # Nominal and effective root counts
    if res.get("nominal_root_count") != spec.nominal_budget:
        raise ValueError("nominal_root_count mismatch")
        
    eff_count = res.get("effective_training_root_count")
    if not isinstance(eff_count, int) or isinstance(eff_count, bool) or not (0 <= eff_count <= spec.nominal_budget):
        raise ValueError(f"effective_training_root_count bounds error: {eff_count}")
        
    # Effective root population digest
    eff_digest = res.get("effective_root_population_digest")
    if not isinstance(eff_digest, str) or len(eff_digest) != 64 or not all(c in "0123456789abcdefABCDEF" for c in eff_digest):
        raise ValueError(f"effective_root_population_digest invalid: expected 64-char hex digest, got {eff_digest}")
    expected_eff_digest = getattr(spec, "effective_root_population_digest", None)
    if expected_eff_digest and eff_digest != expected_eff_digest:
        raise ValueError(f"effective_root_population_digest mismatch: expected {expected_eff_digest}, got {eff_digest}")
        
    # Epochs and validation trace
    epochs = res.get("epochs_completed")
    if not isinstance(epochs, int) or isinstance(epochs, bool) or not (1 <= epochs <= 200):
        raise ValueError(f"epochs_completed bounds error: {epochs}")
        
    val_trace = res.get("validation_trace")
    if not isinstance(val_trace, list) or len(val_trace) != epochs:
        raise ValueError(f"validation_trace length ({len(val_trace) if isinstance(val_trace, list) else None}) inconsistent with epochs_completed ({epochs})")
    for idx, v in enumerate(val_trace):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0.0:
            raise ValueError(f"validation_trace[{idx}] non-finite or negative: {v}")
            
    # Best epoch and best validation NLL (earliest-minimum rule)
    best_epoch = res.get("best_epoch")
    if not isinstance(best_epoch, int) or isinstance(best_epoch, bool) or not (1 <= best_epoch <= epochs):
        raise ValueError(f"best_epoch bounds error: {best_epoch} not in [1, {epochs}]")
        
    best_val_nll = res.get("best_validation_root_nll")
    if not isinstance(best_val_nll, (int, float)) or isinstance(best_val_nll, bool) or not math.isfinite(best_val_nll) or best_val_nll < 0.0:
        raise ValueError(f"best_validation_root_nll non-finite or negative: {best_val_nll}")
        
    min_trace_val = min(val_trace)
    if abs(best_val_nll - min_trace_val) > 1e-9:
        raise ValueError(f"best_validation_root_nll {best_val_nll} != min(validation_trace) {min_trace_val}")
        
    earliest_min_epoch = val_trace.index(min_trace_val) + 1
    if best_epoch != earliest_min_epoch:
        raise ValueError(f"best_epoch {best_epoch} does not match earliest-minimum epoch {earliest_min_epoch}")
        
    # Canonical model state digest
    model_sha = res.get("canonical_model_state_sha")
    if not isinstance(model_sha, str) or len(model_sha) != 64 or not all(c in "0123456789abcdefABCDEF" for c in model_sha):
        raise ValueError(f"canonical_model_state_sha invalid: expected 64-char hex digest, got {model_sha}")
        
    # Test evaluation and test losses
    if res.get("test_evaluation_count") != 1:
        raise ValueError(f"test_evaluation_count != 1: {res.get('test_evaluation_count')}")
        
    if tuple(res.get("test_root_ids", ())) != tuple(spec.test_root_ids):
        raise ValueError("test_root_ids mismatch in worker result")
        
    test_losses = res.get("test_root_losses")
    if not isinstance(test_losses, dict):
        raise ValueError("test_root_losses must be a dict")
        
    expected_test_rids = set(spec.test_root_ids)
    actual_test_rids = set(test_losses.keys())
    if actual_test_rids != expected_test_rids or len(test_losses) != len(spec.test_root_ids):
        missing = expected_test_rids - actual_test_rids
        extra = actual_test_rids - expected_test_rids
        raise ValueError(f"test_root_losses keys do not exactly match test_root_ids: missing {missing}, extra {extra}")
        
    for rid, loss in test_losses.items():
        if not isinstance(loss, (int, float)) or isinstance(loss, bool) or not math.isfinite(loss) or loss < 0.0:
            raise ValueError(f"test_root_losses[{rid}] non-finite or negative: {loss}")
            
    return res

def _validate_single_worker_result(spec: JobSpec, res: Dict):
    return validate_worker_result(spec, res)

def validate_completed_worker_results(job_specs: List[JobSpec], results: List[Dict]):
    if len(results) != len(job_specs):
        raise ValueError(f"Expected {len(job_specs)} results, got {len(results)}")
        
    expected_tuples = {(spec.condition, spec.nominal_budget, spec.seed) for spec in job_specs}
    actual_tuples = {(res["condition"], res["nominal_budget"], res["seed"]) for res in results}
    if actual_tuples != expected_tuples or len(actual_tuples) != len(job_specs):
        raise ValueError("Results tuples incompleteness or duplicates")
        
    res_dict = {(res["condition"], res["nominal_budget"], res["seed"]): res for res in results}
    
    for spec in job_specs:
        res = res_dict[(spec.condition, spec.nominal_budget, spec.seed)]
        validate_worker_result(spec, res)
        
    return "PASS"

def make_sealed_worker_result(spec: JobSpec, worker_result: Dict) -> Dict:
    for k in ["approved_implementation_sha", "protocol_v7_sha", "seal_v2_sha", 
              "label_scientific_sha", "runtime_v3_identity", "runtime_v3_pin_sha",
              "lineage", "replication_seal_sha"]:
        if hasattr(spec, k):
            v = getattr(spec, k)
            if v is not None and k not in worker_result:
                worker_result[k] = v
            
    payload_json = json.dumps(worker_result, sort_keys=True, separators=(',', ':'), allow_nan=False)
    payload_sha = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()
    
    envelope = {
        "schema": "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_SEAL_V1",
        "condition": spec.condition,
        "nominal_budget": spec.nominal_budget,
        "seed": spec.seed,
        "lineage": getattr(spec, "lineage", "V6_HISTORICAL"),
        "approved_implementation_sha": spec.approved_implementation_sha,
        "protocol_v7_sha": spec.protocol_v7_sha,
        "seal_v2_sha": spec.seal_v2_sha,
        "replication_seal_sha": getattr(spec, "replication_seal_sha", None),
        "label_scientific_sha": spec.label_scientific_sha,
        "runtime_v3_identity": spec.runtime_v3_identity,
        "runtime_v3_pin_sha": spec.runtime_v3_pin_sha,
        "nominal_root_population_digest": spec.nominal_root_population_digest,
        "validation_population_digest": spec.validation_population_digest,
        "test_population_digest": spec.test_population_digest,
        "payload_sha256": payload_sha,
        "payload": worker_result
    }
    return envelope

def save_sealed_worker_result(result_dir: str, spec: JobSpec, envelope: Dict) -> str:
    os.makedirs(result_dir, exist_ok=True)
    filename = f"worker_result_{spec.condition}_b{spec.nominal_budget}_s{spec.seed}.json"
    final_path = os.path.join(result_dir, filename)
    
    temp_path = os.path.join(result_dir, f".tmp_{filename}_{os.getpid()}_{uuid.uuid4().hex}")
    content = json.dumps(envelope, sort_keys=True, separators=(',', ':'), allow_nan=False)
    
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
            
        try:
            os.link(temp_path, final_path)
        except FileExistsError:
            raise ValueError(f"Refusing to overwrite existing result file: {final_path}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
                
    try:
        dir_fd = os.open(result_dir, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        pass
    return final_path

def validate_sealed_worker_result(envelope: Dict, spec: JobSpec) -> Dict:
    if not isinstance(envelope, dict):
        raise ValueError("Envelope must be a dict")
    if envelope.get("schema") != "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_SEAL_V1":
        raise ValueError(f"Invalid envelope schema: {envelope.get('schema')}")

    expected_lineage = getattr(spec, "lineage", "V6_HISTORICAL")
    envelope_lineage = envelope.get("lineage", "V6_HISTORICAL")
    if envelope_lineage != expected_lineage:
        raise ValueError(f"Envelope lineage mismatch: expected {expected_lineage}, got {envelope_lineage}")
        
    if envelope.get("condition") != spec.condition:
        raise ValueError("Envelope condition mismatch")
    if envelope.get("nominal_budget") != spec.nominal_budget:
        raise ValueError("Envelope nominal_budget mismatch")
    if envelope.get("seed") != spec.seed:
        raise ValueError("Envelope seed mismatch")
        
    if envelope.get("approved_implementation_sha") != spec.approved_implementation_sha:
        raise ValueError("Envelope approved_implementation_sha mismatch")
    if envelope.get("protocol_v7_sha") != spec.protocol_v7_sha:
        raise ValueError("Envelope protocol_v7_sha mismatch")
    if envelope.get("seal_v2_sha") != spec.seal_v2_sha:
        raise ValueError("Envelope seal_v2_sha mismatch")
    if envelope.get("replication_seal_sha") != getattr(spec, "replication_seal_sha", None):
        raise ValueError("Envelope replication_seal_sha mismatch")
    if envelope.get("label_scientific_sha") != spec.label_scientific_sha:
        raise ValueError("Envelope label_scientific_sha mismatch")
    if envelope.get("runtime_v3_identity") != spec.runtime_v3_identity:
        raise ValueError("Envelope runtime_v3_identity mismatch")
    if envelope.get("runtime_v3_pin_sha") != spec.runtime_v3_pin_sha:
        raise ValueError("Envelope runtime_v3_pin_sha mismatch")
        
    if envelope.get("nominal_root_population_digest") != spec.nominal_root_population_digest:
        raise ValueError("Envelope nominal_root_population_digest mismatch")
    if envelope.get("validation_population_digest") != spec.validation_population_digest:
        raise ValueError("Envelope validation_population_digest mismatch")
    if envelope.get("test_population_digest") != spec.test_population_digest:
        raise ValueError("Envelope test_population_digest mismatch")
        
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Envelope payload must be a dict")
        
    payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
    calculated_sha = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()
    if calculated_sha != envelope.get("payload_sha256"):
        raise ValueError("Envelope payload SHA256 mismatch")
        
    # Enforce identical semantic validation on durable payloads
    validate_worker_result(spec, payload)
        
    return payload

def scan_and_validate_results_directory(result_dir: str, job_specs: List[JobSpec]) -> Dict[Tuple[str, int, int], Dict]:
    if not os.path.exists(result_dir):
        return {}
        
    spec_map = {(s.condition, s.nominal_budget, s.seed): s for s in job_specs}
    expected_filenames = {
        f"worker_result_{s.condition}_b{s.nominal_budget}_s{s.seed}.json": (s.condition, s.nominal_budget, s.seed)
        for s in job_specs
    }
    
    entries = os.listdir(result_dir)
    valid_results = {}
    
    for entry in sorted(entries):
        if entry == ".gitignore":
            continue
            
        full_path = os.path.join(result_dir, entry)
        
        if entry.startswith(".tmp") or entry not in expected_filenames:
            raise ValueError(f"Foreign, partial, or unexpected file in result directory: {entry}")
            
        if not os.path.isfile(full_path):
            raise ValueError(f"Non-file entry in result directory: {entry}")
            
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            envelope = json.loads(content)
        except Exception as e:
            raise ValueError(f"Corrupt or unparseable result file {entry}: {e}")
            
        tuple_key = expected_filenames[entry]
        if tuple_key in valid_results:
            raise ValueError(f"Duplicate result for tuple: {tuple_key}")
            
        spec = spec_map[tuple_key]
        payload = validate_sealed_worker_result(envelope, spec)
        valid_results[tuple_key] = payload
        
    return valid_results

def run_training_parent(
    approved_sha: str,
    cache_path: str,
    cache_sha: str,
    repo_root: str = ".",
    result_dir: Optional[str] = None,
    worker_fn: Optional[Callable[[JobSpec], Dict]] = None,
    lineage: str = "V6_HISTORICAL"
):
    verify_approved_sha_gate(approved_sha, repo_root)
    check_real_training_authorization()
    
    if lineage == "V6_HISTORICAL":
        ev_id = verify_training_evidence_preflight(approved_sha, repo_root)
        if result_dir is None:
            result_dir = "artifacts/research/cp_representation_efficiency_training_v1/worker_results"
        elif os.path.abspath(result_dir) == os.path.abspath(os.path.join(repo_root, "artifacts/research/cp_representation_efficiency_training_v7_rep1/worker_results")):
            raise ValueError("Refusing to reuse replication result directory for historical V6 lineage")
    elif lineage == "V7_REPLICATION_1":
        ev_id = verify_replication_training_evidence_preflight(approved_sha, repo_root)
        if result_dir is None:
            result_dir = "artifacts/research/cp_representation_efficiency_training_v7_rep1/worker_results"
        elif os.path.abspath(result_dir) == os.path.abspath(os.path.join(repo_root, "artifacts/research/cp_representation_efficiency_training_v1/worker_results")):
            raise ValueError("Refusing to reuse historical V6 result directory for replication lineage")
    else:
        raise ValueError(f"Unknown or unsupported lineage: {lineage}")
        
    if cache_sha != ev_id.label_scientific_sha:
        raise ValueError(f"cache_sha MUST exactly equal the canonical label scientific SHA ({ev_id.label_scientific_sha})")
        
    cache = DerivedCache(cache_path, cache_sha)
    populations = build_frozen_populations(cache)
    job_specs = build_job_specs(populations, ev_id, cache_path, approved_sha)
    
    # Resumption scanner: validate existing sealed results
    existing_results = scan_and_validate_results_directory(result_dir, job_specs)
    
    # Calculate missing jobs
    missing_specs = [
        s for s in job_specs
        if (s.condition, s.nominal_budget, s.seed) not in existing_results
    ]
    
    completed_results = dict(existing_results)
    
    if missing_specs:
        target_worker = worker_fn if worker_fn is not None else run_downstream_worker
        def on_success(spec: JobSpec, res: Dict):
            validate_worker_result(spec, res)
            envelope = make_sealed_worker_result(spec, res)
            save_sealed_worker_result(result_dir, spec, envelope)
            
        new_results = run_job_specs(missing_specs, target_worker, on_result_success=on_success)
        for res in new_results:
            tuple_key = (res["condition"], res["nominal_budget"], res["seed"])
            completed_results[tuple_key] = res
            
    # Finalization: require exactly all 160 frozen tuples
    if len(completed_results) != len(job_specs):
        raise ValueError(f"Expected {len(job_specs)} results, got {len(completed_results)}")
        
    ordered_results = [completed_results[(s.condition, s.nominal_budget, s.seed)] for s in job_specs]
    validate_completed_worker_results(job_specs, ordered_results)
    return "STOP_BEFORE_SCIENTIFIC_ANALYSIS"



