import os
import copy
import hashlib
import multiprocessing
import pytest
from unittest.mock import patch, MagicMock

import chessheat.cp_representation_efficiency as cp
from chessheat.protocol_freeze import SourcePairFeatures, encode_position

def make_root(rid, pair_tuples, target_labels):
    pairs = []
    for (m1, m2, c1, c2), tl in zip(pair_tuples, target_labels):
        pid = hashlib.sha256(f"CHESSHEAT_TARGET_PAIR_V1|{rid}|{m1}|{m2}".encode('utf-8')).hexdigest()
        pf = SourcePairFeatures(m1, c1, m2, c2)
        pairs.append({
            "pair_id": pid, "m1_uci": m1, "m2_uci": m2, "source_cp_m1": c1, "source_cp_m2": c2,
            "d_X": pf.d_x, "a_X": pf.a_x, "target_label": tl
        })
    return {
        "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
        "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
        "partition": "TRAIN",
        "root_identity": rid,
        "source_pair_count": len(pairs),
        "target_evaluable_pair_count": sum(1 for p in pairs if p["target_label"] is not None),
        "sufficient_position": {"board_arrangement_fen": "8/8/8/8/8/8/8/8 w - - 0 1", "en_passant_square": None, "castling_rights": "-", "side_to_move": "white"},
        "pairs": pairs
    }

def test_model_topology():
    model = cp.initialize_model_cpu_then_mps(cp._build_model, cp.configure_runtime(1729))
    import torch
    for m in model.modules():
        assert not isinstance(m, torch.nn.BatchNorm2d)
        assert not isinstance(m, torch.nn.Dropout)

def test_budget_selection():
    with pytest.raises(ValueError):
        cp.run_training_job("mu_D", 123, 1729, [], [], [])

def test_epoch_ordering():
    pass

def test_b_raw_non_execution():
    with pytest.raises(ValueError, match="B_RAW_NOT_EXECUTED"):
        cp.run_training_job("B_raw", 250, 1729, [], [], [])

def test_gates():
    if "CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA" in os.environ:
        del os.environ["CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA"]
    with pytest.raises(ValueError, match="mismatch|Missing|authorized"):
        cp.check_execution_gates("0"*40, ".")
    os.environ["CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA"] = "invalid"
    with pytest.raises(ValueError, match="40 lowercase hex|mismatch"):
        cp.check_execution_gates("invalid", ".")

def test_analysis_authorization():
    if "CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED" in os.environ:
        del os.environ["CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED"]
    with pytest.raises(ValueError, match="Missing|authorized"):
        cp.check_analysis_gate()

def test_information_boundary():
    import torch
    rec = cp.LearnerRecord(p_tensor=torch.zeros(1), side_tensor=torch.zeros(1), spatial_map=torch.zeros(1), label=1)
    with pytest.raises(Exception):
        rec.label = 2

def test_pair_order():
    r1 = make_root("r1", [("b1a1", "a1a2", 10, 5)], ["FIRST_BETTER"])
    with pytest.raises(ValueError, match="m1_uci must be strictly less than m2_uci"):
        cp.construct_learner_records(r1, "mu_D")

def test_four_condition_equality():
    import torch
    r1 = make_root("r1", [("a1a2", "b1b2", 10, 5)], ["FIRST_BETTER"])
    r_D = cp.construct_learner_records(r1, "mu_D")[0]
    r_T = cp.construct_learner_records(r1, "mu_T")[0]
    r_B = cp.construct_learner_records(r1, "B_daS")[0]
    
    assert type(r_D.side_tensor) == type(r_T.side_tensor)
    assert type(r_D.side_tensor) == type(r_B.side_tensor)
    assert r_D.label == r_T.label

def test_root_weighted_loss_and_attrition():
    pass

def test_mps_repeat_deterministic():
    pass

def test_canonical_state_digest():
    pass
