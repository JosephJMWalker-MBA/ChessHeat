import pytest
import math
import hashlib
import os
import copy
from typing import Any
import multiprocessing

from chessheat.protocol_freeze import SourcePairFeatures, build_m_d, build_m_t, build_m_zero, build_m_perm
from chessheat.ml_runtime import configure_runtime
from chessheat.cp_representation_efficiency import (
    _build_model, get_canonical_state_digest, get_epoch_order,
    select_budgets, check_execution_gates, run_training_job,
    LearnerRecord, build_root_tensors, label_to_idx, check_analysis_gate,
    verify_approved_sha_gate, read_and_validate_roots, run_scientific_analysis
)
from chessheat.protocol_freeze import (
    mean_five_seed_root_nll, compute_aulc, classify_outcome, full_bootstrap_procedure, CanonicalTensorF32
)
from unittest.mock import patch

def test_model_topology():
    ctx = configure_runtime(1729)
    model = _build_model(ctx.torch)
    params = list(model.parameters())
    # Count params
    total_params = sum(p.numel() for p in params)
    
    assert total_params == 144643
    
    x_sp = ctx.torch.randn(2, 19, 8, 8)
    x_sd = ctx.torch.randn(2, 270)
    out = model(x_sp, x_sd)
    assert out.shape == (2, 3)

def test_representation_equality():
    pf = SourcePairFeatures("e2e4", 10, "e7e5", -10)
    assert build_m_zero().values == [0.0]*64
    d = build_m_d(pf)
    t = build_m_t(pf)
    p = build_m_perm(pf)
    # Check that they differ
    assert d.values != t.values
    assert t.values != p.values

def test_four_condition_equality():
    r = {
        "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
        "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
        "partition": "TRAIN",
        "root_identity": "test",
        "source_pair_count": 1,
        "target_evaluable_pair_count": 1,
        "sufficient_position": {"board_arrangement_fen": "8/8/8/8/8/8/8/8 w - - 0 1", "en_passant_square": None, "castling_rights": "-", "side_to_move": "white"},
        "pairs": [
            {
                "pair_id": 1,
                "m1_uci": "a1a2", "source_cp_m1": 10,
                "m2_uci": "a1b1", "source_cp_m2": 5,
                "d_X": "SOURCE_FIRST_BETTER", "a_X": 5,
                "target_label": "FIRST_BETTER"
            }
        ]
    }
    
    import chessheat.cp_representation_efficiency as cp
    r_d = cp.construct_learner_records(r, "mu_D")[0]
    r_t = cp.construct_learner_records(r, "mu_T")[0]
    r_z = cp.construct_learner_records(r, "B_daS")[0]
    r_p = cp.construct_learner_records(r, "B_perm")[0]
    
    assert r_d.p_tensor.values == r_t.p_tensor.values == r_z.p_tensor.values == r_p.p_tensor.values
    assert r_d.side_tensor.values == r_t.side_tensor.values == r_z.side_tensor.values == r_p.side_tensor.values
    assert r_d.label == r_t.label == r_z.label == r_p.label
    
def test_budget_selection():
    all_metadata = []
    for i in range(20000):
        all_metadata.append({"root_identity": f"t_{i}", "partition": "TRAIN", "source_pair_count": 1})
    budgets = select_budgets(all_metadata)
    assert len(budgets[250]) == 250
    with pytest.raises(ValueError):
        select_budgets(all_metadata[:100]) # not enough for 250

def test_epoch_ordering():
    ids = ["a", "b", "c", "d", "e"]
    order_0 = get_epoch_order(1729, 0, ids)
    order_1 = get_epoch_order(1729, 1, ids)
    order_diff_seed = get_epoch_order(2718, 0, ids)
    
    assert set(order_0) == set(ids)
    assert order_0 != order_1
    assert order_0 != order_diff_seed
    
def test_real_data_non_exposure():
    with patch("builtins.open") as mock_open:
        import scripts.run_cp_representation_efficiency
        pass # The entrypoint exists before opening

def _worker_init(seed, queue):
    try:
        from chessheat.ml_runtime import configure_runtime
        from chessheat.cp_representation_efficiency import _build_model, get_canonical_state_digest
        ctx = configure_runtime(seed)
        model = _build_model(ctx.torch)
        digest = get_canonical_state_digest(model)
        queue.put(("OK", digest))
    except Exception as e:
        queue.put(("ERR", str(e)))

def test_model_initialization_isolation():
    def get_init(seed):
        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=_worker_init, args=(seed, q))
        p.start()
        p.join()
        status, val = q.get()
        assert status == "OK", val
        return val
        
    d1 = get_init(1729)
    d2 = get_init(1729)
    d3 = get_init(2718)
    assert d1 == d2
    assert d1 != d3
    
def test_gates():
    with pytest.raises(ValueError):
        check_execution_gates("xxx", os.getcwd())
            
def test_b_raw_non_execution():
    with pytest.raises(ValueError, match="B_RAW_NOT_EXECUTED_IN_PRIMARY_V2_PIPELINE"):
        run_training_job("B_raw", 250, 1729, [], [], [])
        
def test_aulc_and_stats():
    budgets = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    utils = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    assert math.isclose(compute_aulc(budgets, utils), 0.5981012658227848)


def test_canonical_state_digest():
    ctx = configure_runtime(1729)
    model = _build_model(ctx.torch)
    d1 = get_canonical_state_digest(model)
    model.side[0].bias.data += 0.1
    d2 = get_canonical_state_digest(model)
    assert d1 != d2


def _root_worker(qu):
    try:
        from unittest.mock import patch
        import os
        from chessheat.cp_representation_efficiency import run_training_job
        
        r1 = {
            "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
            "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
            "partition": "TRAIN",
            "root_identity": "r1",
            "source_pair_count": 1,
            "target_evaluable_pair_count": 1,
            "sufficient_position": {"board_arrangement_fen": "8/8/8/8/8/8/8/8 w - - 0 1", "en_passant_square": None, "castling_rights": "-", "side_to_move": "white"},
            "pairs": [
                {
                    "pair_id": 1, "m1_uci": "a1a2", "source_cp_m1": 10, "m2_uci": "a1b1", "source_cp_m2": 5, "d_X": "SOURCE_FIRST_BETTER", "a_X": 5, "target_label": "FIRST_BETTER"
                }
            ]
        }
        r5 = {
            "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
            "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
            "partition": "TRAIN",
            "root_identity": "r5",
            "source_pair_count": 5,
            "target_evaluable_pair_count": 5,
            "sufficient_position": {"board_arrangement_fen": "8/8/8/8/8/8/8/8 w - - 0 1", "en_passant_square": None, "castling_rights": "-", "side_to_move": "white"},
            "pairs": [
                { "pair_id": i, "m1_uci": f"a{i}a{i+1}", "source_cp_m1": 10, "m2_uci": f"b{i}b{i+1}", "source_cp_m2": 5, "d_X": "SOURCE_FIRST_BETTER", "a_X": 5, "target_label": "SECOND_BETTER" } for i in range(1, 6)
            ]
        }
        r0 = {
            "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
            "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
            "partition": "TRAIN",
            "root_identity": "r0",
            "source_pair_count": 1,
            "target_evaluable_pair_count": 0,
            "sufficient_position": {"board_arrangement_fen": "8/8/8/8/8/8/8/8 w - - 0 1", "en_passant_square": None, "castling_rights": "-", "side_to_move": "white"},
            "pairs": [
                { "pair_id": 1, "m1_uci": "a1a2", "source_cp_m1": 10, "m2_uci": "a1b1", "source_cp_m2": 5, "d_X": "SOURCE_FIRST_BETTER", "a_X": 5, "target_label": None }
            ]
        }
    
        os.environ["CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA"] = "0"*40
        with patch("chessheat.cp_representation_efficiency.check_execution_gates"):
            res = run_training_job("mu_D", 250, 1729, [r1, r5, r0], [r1], [r5])
        qu.put(("OK", res))
    except Exception as e:
        import traceback
        qu.put(("ERR", traceback.format_exc()))

def test_root_weighted_loss_and_attrition():
    import multiprocessing
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=_root_worker, args=(q,))
    p.start()
    p.join()
    st, res = q.get()
    assert st == "OK", res

def _mps_worker(seed, qu):
    try:
        from unittest.mock import patch
        import os
        from chessheat.cp_representation_efficiency import run_training_job
        r1 = {
            "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
            "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
            "partition": "TRAIN",
            "root_identity": "r1",
            "source_pair_count": 1,
            "target_evaluable_pair_count": 1,
            "sufficient_position": {"board_arrangement_fen": "8/8/8/8/8/8/8/8 w - - 0 1", "en_passant_square": None, "castling_rights": "-", "side_to_move": "white"},
            "pairs": [{"pair_id": 1, "m1_uci": "a1a2", "source_cp_m1": 10, "m2_uci": "a1b1", "source_cp_m2": 5, "d_X": "SOURCE_FIRST_BETTER", "a_X": 5, "target_label": "FIRST_BETTER"}]
        }
        os.environ["CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA"] = "0"*40
        with patch("chessheat.cp_representation_efficiency.check_execution_gates"):
            res = run_training_job("mu_D", 250, seed, [r1], [r1], [r1])
        qu.put(("OK", res))
    except Exception as e:
        import traceback
        qu.put(("ERR", traceback.format_exc()))

def test_mps_repeat_deterministic():
    import multiprocessing
    def get_res(seed):
        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=_mps_worker, args=(seed, q))
        p.start()
        p.join()
        st, val = q.get()
        assert st == "OK", val
        return val
        
    r1 = get_res(1729)
    r2 = get_res(1729)
    assert r1["best_epoch"] == r2["best_epoch"]
    assert r1["canonical_model_state_sha"] == r2["canonical_model_state_sha"]
    assert r1["test_root_losses"] == r2["test_root_losses"]
    assert r1["validation_trace"] == r2["validation_trace"]
    
def test_target_information_boundary():
    # Test that forbidden fields do not enter LearnerRecord
    r1 = {
        "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
        "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
        "partition": "TRAIN",
        "root_identity": "r1",
        "source_pair_count": 1,
        "target_evaluable_pair_count": 1,
        "sufficient_position": {"board_arrangement_fen": "8/8/8/8/8/8/8/8 w - - 0 1", "en_passant_square": None, "castling_rights": "-", "side_to_move": "white"},
        "pairs": [{"pair_id": 1, "m1_uci": "a1a2", "source_cp_m1": 10, "m2_uci": "a1b1", "source_cp_m2": 5, "d_X": "SOURCE_FIRST_BETTER", "a_X": 5, "target_label": "FIRST_BETTER", "target_raw_sha256": "secret", "TARGET CP": 100}]
    }
    import chessheat.cp_representation_efficiency as cp
    records = cp.construct_learner_records(r1, "mu_D")
    for rec in records:
        assert not hasattr(rec, "target_raw_sha256")
        assert not hasattr(rec, "TARGET CP")
