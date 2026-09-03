import math
import os
import json
import hashlib
import re
import copy
import subprocess
from typing import Dict, List, Any, Tuple, Optional
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

def evaluate_roots(model, root_records_tensors: Dict[str, Any], root_ids: List[str], torch):
    model.eval()
    root_nlls = {}
    loss_fn = torch.nn.CrossEntropyLoss(reduction='none')
    with torch.no_grad():
        for rid in root_ids:
            if rid not in root_records_tensors:
                continue
            x_spatial, x_side, y = root_records_tensors[rid]
            logits = model(x_spatial, x_side)
            loss = loss_fn(logits, y).mean()
            root_nlls[rid] = loss.item()
    return root_nlls

def run_training_job(
    condition: str,
    nominal_budget: int,
    seed: int,
    training_root_records: List[Dict],
    validation_root_records: List[Dict],
    test_root_records: List[Dict],
    nominal_root_population_digest: str,
    validation_population_digest: str,
    test_population_digest: str
):
    if condition == "B_raw":
        raise ValueError("B_RAW_NOT_EXECUTED_IN_PRIMARY_V2_PIPELINE")
        
    valid_budgets = {250, 500, 1000, 2000, 4000, 8000, 16000, 20000}
    if nominal_budget not in valid_budgets:
        raise ValueError("Invalid budget")
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
        
    ctx = configure_runtime(seed)
    torch = ctx.torch
    device = ctx.device
    
    model = initialize_model_cpu_then_mps(_build_model, ctx)
    optimizer = build_frozen_adam(model, torch)
    loss_fn = torch.nn.CrossEntropyLoss(reduction='none')
    
    training_root_records = read_and_validate_roots(training_root_records)
    validation_root_records = read_and_validate_roots(validation_root_records)
    test_root_records = read_and_validate_roots(test_root_records)
    
    effective_train_roots = {}
    for r in training_root_records:
        recs = construct_learner_records(r, condition)
        if recs:
            effective_train_roots[r["root_identity"]] = build_root_tensors(torch, recs, device)
            
    val_roots = {}
    for r in validation_root_records:
        recs = construct_learner_records(r, condition)
        if not recs:
            raise ValueError("Fail if 0-evaluable roots in val/test")
        val_roots[r["root_identity"]] = build_root_tensors(torch, recs, device)
            
    test_roots = {}
    for r in test_root_records:
        recs = construct_learner_records(r, condition)
        if not recs:
            raise ValueError("Fail if 0-evaluable roots in val/test")
        test_roots[r["root_identity"]] = build_root_tensors(torch, recs, device)

    if not val_roots:
        raise ValueError("Validation population cannot be empty.")
        
    best_val_nll = float('inf')
    best_epoch = -1
    best_state_digest = None
    best_state_dict = None
    patience = 20
    non_improvement = 0
    val_trace = []
    
    effective_root_ids = [r["root_identity"] for r in training_root_records if r["root_identity"] in effective_train_roots]
    effective_root_population_digest = canonical_root_population_digest(effective_root_ids)
    val_root_ids = [r["root_identity"] for r in validation_root_records]
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
                x_spatial, x_side, y = effective_train_roots[rid]
                logits = model(x_spatial, x_side)
                root_loss = loss_fn(logits, y).mean()
                total_loss += root_loss
            if B > 0:
                (total_loss / B).backward()
                optimizer.step()
            
        val_nlls = evaluate_roots(model, val_roots, val_root_ids, torch)
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
    
    test_root_ids = [r["root_identity"] for r in test_root_records]
    test_nlls = evaluate_roots(model, test_roots, test_root_ids, torch)
    test_eval_count += 1
    
    return {
        "schema": "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V13",
        "condition": condition,
        "nominal_budget": nominal_budget,
        "seed": seed,
        "nominal_root_count": len(training_root_records),
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
        "test_root_ids": tuple(test_root_ids),
        "test_root_losses": test_nlls,
        "canonical_model_state_sha": best_state_digest
    }

def run_scientific_analysis(worker_results: List[Dict]):
    check_analysis_gate()
    
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
    seal_v2_sha: str
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
        label_compressed_sha="dea9346f9cb125f9c35e8824bb937daf4ea7fc51cff7f6c7c437caac8ae2c92d"
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
    seal_v2_sha: str
    label_scientific_sha: str
    runtime_v3_identity: str
    runtime_v3_pin_sha: str
    approved_implementation_sha: str
    cache_path: str

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
                    cache_path=cache_path
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

def run_job_specs(job_specs: List[JobSpec], worker_fn):
    import multiprocessing
    import queue
    results = []
    
    for spec in job_specs:
        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=_process_wrapper, args=(spec, worker_fn, q))
        p.start()
        
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
        
        p.join()
        
        if p.exitcode != 0:
            raise RuntimeError(f"Process crashed with exit code {p.exitcode}")
            
        if res_tuple is None:
            raise RuntimeError("Process died without returning a result")
            
        success, res = res_tuple
        if not success:
            raise res
        results.append(res)
        
    return results





def run_downstream_worker(spec: JobSpec):
    cache = DerivedCache(spec.cache_path, spec.label_scientific_sha)
    
    def get_and_validate(rids):
        res = []
        for r in rids:
            root = cache.get_root(r)
            if not root: raise ValueError(f"Root {r} not found")
            res.append(root)
        return read_and_validate_roots(res)
        
    nominal = get_and_validate(spec.nominal_root_ids)
    val = get_and_validate(spec.validation_root_ids)
    test = get_and_validate(spec.test_root_ids)
    
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
        training_root_records=nominal,
        validation_root_records=val,
        test_root_records=test,
        nominal_root_population_digest=spec.nominal_root_population_digest,
        validation_population_digest=spec.validation_population_digest,
        test_population_digest=spec.test_population_digest,
    )
    
    # Binding and Validating Result
    if result.get("schema") not in ["CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V12", "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V13"]:
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
    result["label_scientific_sha"] = spec.label_scientific_sha
    result["runtime_v3_identity"] = spec.runtime_v3_identity
    result["runtime_v3_pin_sha"] = spec.runtime_v3_pin_sha
    
    return result

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
        
        if res["schema"] not in ["CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V12", "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V13"]:
            raise ValueError("Schema mismatch in parent validation")
            
        if res["approved_implementation_sha"] != spec.approved_implementation_sha:
            raise ValueError("approved_implementation_sha mismatch")
        if res["protocol_v7_sha"] != spec.protocol_v7_sha:
            raise ValueError("protocol_v7_sha mismatch")
        if res["seal_v2_sha"] != spec.seal_v2_sha:
            raise ValueError("seal_v2_sha mismatch")
        if res["label_scientific_sha"] != spec.label_scientific_sha:
            raise ValueError("label_scientific_sha mismatch")
        if res["runtime_v3_identity"] != spec.runtime_v3_identity:
            raise ValueError("runtime_v3_identity mismatch")
        if res["runtime_v3_pin_sha"] != spec.runtime_v3_pin_sha:
            raise ValueError("runtime_v3_pin_sha mismatch")
            
        if res["nominal_root_population_digest"] != spec.nominal_root_population_digest:
            raise ValueError("nominal_root_population_digest mismatch")
        if res["validation_population_digest"] != spec.validation_population_digest:
            raise ValueError("validation_population_digest mismatch")
        if res["test_population_digest"] != spec.test_population_digest:
            raise ValueError("test_population_digest mismatch")
            
        if tuple(res["test_root_ids"]) != tuple(spec.test_root_ids):
            raise ValueError("test_root_ids mismatch in parent")
            
    return "PASS"

def run_training_parent(approved_sha: str, cache_path: str, cache_sha: str, repo_root: str = "."):
    verify_approved_sha_gate(approved_sha, repo_root)
    check_real_training_authorization()
    ev_id = verify_training_evidence_preflight(approved_sha, repo_root)
    
    if cache_sha != ev_id.label_scientific_sha:
        raise ValueError("cache_sha MUST exactly equal the canonical label scientific SHA")
        
    cache = DerivedCache(cache_path, cache_sha)
    populations = build_frozen_populations(cache)
    job_specs = build_job_specs(populations, ev_id, cache_path, approved_sha)
    
    results = run_job_specs(job_specs, run_downstream_worker)
    validate_completed_worker_results(job_specs, results)
    return "STOP_BEFORE_SCIENTIFIC_ANALYSIS"



