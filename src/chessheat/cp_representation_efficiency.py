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
    import os
    if os.environ.get("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA") != approved_sha:
        raise ValueError("Missing or mismatched CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA")
    if not isinstance(approved_sha, str) or not re.match(r"^[0-9a-f]{40}$", approved_sha):
        raise ValueError("SHA must be exactly 40 lowercase hexadecimal characters.")
        
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
    def __init__(self, filepath: str = None):
        self.filepath = filepath
        self.roots = {}
        if filepath:
            self._build_index()
            
    def _build_index(self):
        import json
        with open(self.filepath, "rb") as f:
            offset = 0
            for line in f:
                length = len(line)
                rec = json.loads(line)
                rid = rec["root_identity"]
                if rid in self.roots:
                    raise ValueError("Duplicate root_identity")
                self.roots[rid] = {
                    "root_identity": rid,
                    "byte_offset": offset,
                    "byte_length": length,
                    "partition": rec.get("partition"),
                    "source_pair_count": rec.get("source_pair_count", 0),
                    "target_evaluable_pair_count": rec.get("target_evaluable_pair_count", 0)
                }
                offset += length
                
    def put(self, rid, data):
        self.roots[rid] = data
        
    def get_root(self, rid: str) -> Dict:
        import json
        if not self.filepath:
            return self.roots.get(rid)
        info = self.roots.get(rid)
        if not info:
            return None
        with open(self.filepath, "rb") as f:
            f.seek(info["byte_offset"])
            bytes_data = f.read(info["byte_length"])
            rec = json.loads(bytes_data)
            if rec["root_identity"] != rid:
                raise ValueError("Cache index mismatch")
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
    required_fields = ['schema', 'label_derivation_protocol', 'label_derivation_software_revision', 'protocol_id', 'protocol_json_sha256', 'source_raw_sha256', 'target_raw_sha256', 'target_seal_v2_sha256', 'manifest_sha256', 'root_identity', 'root_record_digest', 'sufficient_position', 'conservative_split_group', 'partition', 'source_status', 'target_status', 'source_cp_move_count', 'source_pair_count', 'target_evaluable_pair_count', 'target_non_evaluable_pair_count', 'pairs']
    for p in records:
        for f in required_fields:
            if f not in p:
                raise ValueError(f"Missing required field: {f}")
        if "schema" not in p:
            raise ValueError("missing schema")
        if "protocol_id" not in p:
            raise ValueError("missing protocol_id")
            
        sp = p.get("sufficient_position", {})
        if sp.get("side_to_move") not in {"w", "b"}:
            raise ValueError("side_to_move must be w or b")
            
        eval_c = p.get("target_evaluable_pair_count", 0)
        noneval_c = p.get("target_non_evaluable_pair_count", 0)
        src_c = p.get("source_pair_count", 0)
        
        if eval_c + noneval_c != src_c:
            raise ValueError("Count mismatch")
            
        prev_pair_id = None
        for pair in p.get("pairs", []):
            m1 = pair["m1_uci"]
            m2 = pair["m2_uci"]
            if not (m1 < m2):
                raise ValueError("m1 must be less than m2")
            
            import hashlib
            expected_sha = hashlib.sha256(f"{m1}|{m2}".encode()).hexdigest()
            if pair["pair_id"] != expected_sha:
                raise ValueError("pair_id SHA mismatch")
                
            if prev_pair_id and pair["pair_id"] <= prev_pair_id:
                raise ValueError("pairs must be strictly lexically ordered by pair_id")
            prev_pair_id = pair["pair_id"]
            
            cp = pair.get("source_m1_m2_cp_delta")
            if cp is not None and isinstance(cp, bool):
                raise ValueError("CP cannot be boolean")
                
            tl = pair.get("target_label")
            if tl not in {"FIRST_BETTER", "EQUAL", "SECOND_BETTER", None}:
                raise ValueError("Invalid target label")
                
            if tl is None:
                if pair.get("target_non_evaluable_reason") != "TARGET_ACQUISITION_FAILURE":
                    raise ValueError("Null target label requires TARGET_ACQUISITION_FAILURE")
                    
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
    nominal_root_population_digest: str = "",
    validation_population_digest: str = "",
    test_population_digest: str = ""
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

    if nominal_root_population_digest:
        calculated_train_digest = hashlib.sha256(b"|".join(r["root_identity"].encode() for r in training_root_records)).hexdigest()
        if calculated_train_digest != nominal_root_population_digest:
            raise ValueError("Train population digest mismatch")
    if validation_population_digest:
        calculated_val_digest = hashlib.sha256(b"|".join(r["root_identity"].encode() for r in validation_root_records)).hexdigest()
        if calculated_val_digest != validation_population_digest:
            raise ValueError("Validation population digest mismatch")
    if test_population_digest:
        calculated_test_digest = hashlib.sha256(b"|".join(r["root_identity"].encode() for r in test_root_records)).hexdigest()
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
    
    effective_root_ids = sorted(list(effective_train_roots.keys()))
    val_root_ids = sorted(list(val_roots.keys()))
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
    
    test_root_ids = sorted(list(test_roots.keys()))
    test_nlls = evaluate_roots(model, test_roots, test_root_ids, torch)
    test_eval_count += 1
    
    return {
        "schema": "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V6",
        "condition": condition,
        "nominal_budget": nominal_budget,
        "nominal_root_count": len(training_root_records),
        "effective_training_root_count": len(effective_root_ids),
        "seed": seed,
        "best_epoch": best_epoch,
        "best_validation_root_nll": best_val_nll,
        "epochs_completed": epoch + 1,
        "validation_trace": val_trace,
        "test_evaluation_count": test_eval_count,
        "test_root_ids": test_root_ids,
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

def verify_training_evidence_preflight(paths: List[str]):
    identities = []
    for path in paths:
        if not os.path.exists(path):
            raise ValueError(f"Path does not exist: {path}")
        with open(path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
            identities.append(h)
    return identities

def build_frozen_populations(cache: DerivedCache, synthetic_budgets: List[int] = None):
    budgets = synthetic_budgets or [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    
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
                
    train_roots = sorted(train_roots, key=lambda rid: canonical_budget_order(rid))
    return train_roots, budgets, val_roots, test_roots, "digests"

def build_job_specs(populations):
    specs = []
    conditions = ["mu_D", "mu_T", "B_daS", "B_perm"]
    train_roots, budgets, val_roots, test_roots, _ = populations
    for cond in conditions:
        for b in budgets:
            for s in [0, 1, 2, 3, 4]:
                specs.append({
                    "condition": cond,
                    "budget": b,
                    "seed": s,
                    "nominal_root_ids": train_roots[:b],
                    "validation_ids": val_roots,
                    "test_ids": test_roots
                })
    return specs

def run_job_specs(job_specs: List[Dict], worker_fn):
    import multiprocessing
    results = []
    with multiprocessing.Pool(processes=len(job_specs)) as pool:
        for res in pool.map(worker_fn, job_specs):
            if isinstance(res, Exception):
                raise res
            results.append(res)
    return results
