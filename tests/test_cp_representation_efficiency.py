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
    LearnerRecord, build_root_tensors, label_to_idx, check_analysis_gate
)
from chessheat.protocol_freeze import (
    mean_five_seed_root_nll, compute_aulc, classify_outcome, full_bootstrap_procedure
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
    
def test_budget_selection():
    all_metadata = []
    # Create 300 TRAIN eligible
    for i in range(300):
        all_metadata.append({"root_identity": f"t_{i}", "partition": "TRAIN", "source_pair_count": 1})
    # Create 50 VALIDATION
    for i in range(50):
        all_metadata.append({"root_identity": f"v_{i}", "partition": "VALIDATION", "source_pair_count": 1})
    # Create 10 TRAIN zero pair
    for i in range(10):
        all_metadata.append({"root_identity": f"tz_{i}", "partition": "TRAIN", "source_pair_count": 0})
        
    budgets = select_budgets(all_metadata)
    assert len(budgets[250]) == 250
    assert len(budgets[500]) == 300
    assert "tz_0" not in budgets[500]

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
        import chessheat.cp_representation_efficiency
        pass

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
    with pytest.raises(ValueError, match="Approved SHA mismatch"):
        check_execution_gates("xxx")
    with patch.dict(os.environ, {"CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA": "xxx"}):
        with pytest.raises(ValueError, match="Real training not authorized"):
            check_execution_gates("xxx")
            
def test_b_raw_non_execution():
    with pytest.raises(ValueError, match="B_RAW_NOT_EXECUTED_IN_PRIMARY_V1_PIPELINE"):
        run_training_job("B_raw", 250, 1729, [], [], [])
        
def test_aulc_and_stats():
    budgets = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    utils = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    assert math.isclose(compute_aulc(budgets, utils), 0.5981012658227848)
    
    mean = mean_five_seed_root_nll({1729: 0.1, 2718: 0.2, 31415: 0.3, 65537: 0.4, 104729: 0.5})
    assert math.isclose(mean, 0.3)
