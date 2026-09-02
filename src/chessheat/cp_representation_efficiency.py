import os
import json
import hashlib
from typing import Dict, List, Any, Tuple
import copy
from .protocol_freeze import (
    SourcePairFeatures, encode_position, encode_side_information,
    build_m_d, build_m_t, build_m_zero, build_m_perm,
    get_partition, canonical_budget_order, mean_five_seed_root_nll,
    compute_aulc, full_bootstrap_procedure, classify_outcome, CanonicalTensorF32
)
from .ml_runtime import configure_runtime, initialize_model_cpu_then_mps, build_frozen_adam

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

class LearnerRecord:
    def __init__(self, p_tensor: CanonicalTensorF32, side_tensor: CanonicalTensorF32,
                 spatial_map: CanonicalTensorF32, label: int):
        self.p_tensor = p_tensor
        self.side_tensor = side_tensor
        self.spatial_map = spatial_map
        self.label = label

def get_epoch_order(seed: int, epoch: int, root_ids: List[str]) -> List[str]:
    def sort_key(rid: str):
        digest = hashlib.sha256(f"CHESSHEAT_MINIBATCH_V3|{seed}|{epoch}|{rid}".encode("utf-8")).hexdigest()
        return (digest, rid)
    return sorted(root_ids, key=sort_key)

def get_canonical_state_digest(model) -> str:
    # CPU contiguous raw tensor bytes in a prospectively fixed canonical byte order
    sd = model.state_dict()
    h = hashlib.sha256()
    h.update(b"CHESSHEAT_MODEL_STATE_V1\n")
    for k in sorted(sd.keys()):
        t = sd[k].cpu().contiguous()
        name_b = k.encode("utf-8")
        dtype_b = str(t.dtype).encode("utf-8")
        shape_b = str(list(t.shape)).encode("utf-8")
        h.update(name_b + b"\n" + dtype_b + b"\n" + shape_b + b"\n")
        
        # PyTorch uses little endian standard representation. Convert to raw bytes.
        # tolist is slow, let's use bytes(t.untyped_storage())
        h.update(bytes(t.untyped_storage()))
    return h.hexdigest()

def check_execution_gates(approved_sha: str):
    actual_sha = os.environ.get("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA")
    if actual_sha != approved_sha:
        raise ValueError(f"Approved SHA mismatch. Expected {approved_sha}, got {actual_sha}")
    if os.environ.get("CHESSHEAT_REAL_TRAINING_AUTHORIZED") != "1":
        raise ValueError("Real training not authorized")

def check_analysis_gate():
    if os.environ.get("CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED") != "1":
        raise ValueError("Scientific analysis not authorized")
        
def label_to_idx(target_label: str) -> int:
    if target_label == "FIRST_BETTER": return 0
    if target_label == "EQUAL": return 1
    if target_label == "SECOND_BETTER": return 2
    raise ValueError("Invalid target label")

def select_budgets(all_roots_metadata: List[Dict]) -> Dict[int, List[str]]:
    eligible = []
    for r in all_roots_metadata:
        if r["partition"] == "TRAIN" and r["source_pair_count"] > 0:
            eligible.append(r["root_identity"])
            
    eligible.sort(key=canonical_budget_order)
    budgets = {}
    for n in [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]:
        if n <= len(eligible):
            budgets[n] = eligible[:n]
        else:
            budgets[n] = list(eligible)
    return budgets

def prepare_data(artifact_path: str, condition: str, nominal_budget_roots: List[str]):
    # In real execution this would use the DERIVED cache or parse the .jsonl.zst. 
    # For now, it mocks it or reads from synthetic JSON if passed.
    # The actual implementation must NEVER read the real zst unless authorized.
    # We will accept a list of root records directly for training to avoid huge parsing in V1 core.
    pass

def construct_learner_records(root_record: Dict, condition: str) -> List[LearnerRecord]:
    p = encode_position(root_record["sufficient_position"])
    records = []
    for pair in root_record["pairs"]:
        if pair.get("target_label") is None:
            continue
            
        pf = SourcePairFeatures(pair["m1_uci"], pair["source_cp_m1"], 
                                pair["m2_uci"], pair["source_cp_m2"])
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
            
        label = label_to_idx(pair["target_label"])
        records.append(LearnerRecord(p, side, m, label))
    return records

def build_root_tensors(torch, records: List[LearnerRecord], device):
    if not records:
        return None
    spatial_list = []
    side_list = []
    labels = []
    for r in records:
        # P is [18, 8, 8], m is [8, 8]. Concat to [19, 8, 8]
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
    loss_fn = torch.nn.CrossEntropyLoss(reduction='mean')
    with torch.no_grad():
        for rid in root_ids:
            if rid not in root_records_tensors:
                continue
            x_spatial, x_side, y = root_records_tensors[rid]
            logits = model(x_spatial, x_side)
            loss = loss_fn(logits, y)
            root_nlls[rid] = loss.item()
    return root_nlls

def run_training_job(
    condition: str,
    nominal_budget: int,
    seed: int,
    training_root_records: List[Dict],
    validation_root_records: List[Dict],
    test_root_records: List[Dict]
):
    if condition == "B_raw":
        raise ValueError("B_RAW_NOT_EXECUTED_IN_PRIMARY_V1_PIPELINE")
        
    ctx = configure_runtime(seed)
    torch = ctx.torch
    device = ctx.device
    
    model = initialize_model_cpu_then_mps(_build_model, ctx)
    optimizer = build_frozen_adam(model, torch)
    loss_fn = torch.nn.CrossEntropyLoss(reduction='mean')
    
    # Target attrition
    effective_train_roots = {}
    for r in training_root_records:
        recs = construct_learner_records(r, condition)
        if recs:
            effective_train_roots[r["root_identity"]] = build_root_tensors(torch, recs, device)
            
    val_roots = {}
    for r in validation_root_records:
        recs = construct_learner_records(r, condition)
        if recs:
            val_roots[r["root_identity"]] = build_root_tensors(torch, recs, device)
            
    test_roots = {}
    for r in test_root_records:
        recs = construct_learner_records(r, condition)
        if recs:
            test_roots[r["root_identity"]] = build_root_tensors(torch, recs, device)

    best_val_nll = float('inf')
    best_epoch = -1
    best_state_digest = None
    best_state_dict = None
    patience = 20
    non_improvement = 0
    val_trace = []
    
    effective_root_ids = sorted(list(effective_train_roots.keys()))
    val_root_ids = sorted(list(val_roots.keys()))
    
    for epoch in range(200):
        model.train()
        epoch_root_ids = get_epoch_order(seed, epoch, effective_root_ids)
        
        for i in range(0, len(epoch_root_ids), 64):
            batch_rids = epoch_root_ids[i:i+64]
            optimizer.zero_grad()
            B = len(batch_rids)
            for rid in batch_rids:
                x_spatial, x_side, y = effective_train_roots[rid]
                logits = model(x_spatial, x_side)
                root_loss = loss_fn(logits, y)
                (root_loss / B).backward()
            optimizer.step()
            
        # Validation
        val_nlls = evaluate_roots(model, val_roots, val_root_ids, torch)
        if not val_nlls:
            val_loss = 0.0
        else:
            val_loss = sum(val_nlls.values()) / len(val_nlls)
            
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
            
    # Restore best checkpoint
    model.load_state_dict(best_state_dict)
    
    # Evaluate test exactly once
    test_root_ids = sorted(list(test_roots.keys()))
    test_nlls = evaluate_roots(model, test_roots, test_root_ids, torch)
    
    return {
        "schema": "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V1",
        "condition": condition,
        "nominal_budget": nominal_budget,
        "effective_training_root_count": len(effective_root_ids),
        "seed": seed,
        "best_epoch": best_epoch,
        "best_validation_root_nll": best_val_nll,
        "epochs_completed": epoch + 1,
        "validation_trace": val_trace,
        "test_evaluation_count": 1,
        "test_root_losses": test_nlls,
        "canonical_model_state_sha": best_state_digest
    }
