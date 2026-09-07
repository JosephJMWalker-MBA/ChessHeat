import os
import json
import shutil
import hashlib
import pytest
from typing import List, Dict

import chessheat.cp_representation_efficiency as cp
from chessheat.cp_representation_efficiency import (
    JobSpec,
    make_sealed_worker_result,
    save_sealed_worker_result,
    validate_sealed_worker_result,
    scan_and_validate_results_directory,
    validate_completed_worker_results,
    check_real_training_authorization,
    check_analysis_authorization
)


def _make_fake_job_spec(condition="mu_D", budget=250, seed=1729, approved_sha="a"*40) -> JobSpec:
    test_rids = tuple(f"CHESSHEAT_TARGET_ROOT_test{i:04d}" for i in range(5))
    return JobSpec(
        condition=condition,
        nominal_budget=budget,
        seed=seed,
        nominal_root_ids=tuple(f"r{i}" for i in range(budget)),
        nominal_root_population_digest="nd_" + condition + f"_{budget}_{seed}",
        validation_root_ids=tuple(f"v{i}" for i in range(5)),
        validation_population_digest="vd_const",
        test_root_ids=test_rids,
        test_population_digest="td_const",
        protocol_v7_sha="ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef",
        seal_v2_sha="2e4735f40124f4eb7017ff816a4ea55e9f72ac559236a6077a0104273b1ab9c4",
        label_scientific_sha="c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2",
        runtime_v3_identity="CHESSHEAT_ML_RUNTIME_V3",
        runtime_v3_pin_sha="e69ae6bcbf96a327b021665b5ac21b63c269cd821be84d567867058b09e98932",
        approved_implementation_sha=approved_sha,
        cache_path="dummy_cache_path"
    )


def _make_fake_worker_result(spec: JobSpec) -> Dict:
    test_losses = {rid: 0.5 for rid in spec.test_root_ids}
    return {
        "schema": "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V14",
        "condition": spec.condition,
        "nominal_budget": spec.nominal_budget,
        "seed": spec.seed,
        "nominal_root_count": spec.nominal_budget,
        "nominal_root_population_digest": spec.nominal_root_population_digest,
        "effective_training_root_count": spec.nominal_budget,
        "effective_root_population_digest": spec.nominal_root_population_digest,
        "validation_population_digest": spec.validation_population_digest,
        "test_population_digest": spec.test_population_digest,
        "best_epoch": 5,
        "best_validation_root_nll": 0.45,
        "epochs_completed": 10,
        "validation_trace": [0.6, 0.55, 0.5, 0.45, 0.46, 0.47],
        "test_evaluation_count": 1,
        "test_root_ids": tuple(spec.test_root_ids),
        "test_root_losses": test_losses,
        "canonical_model_state_sha": "f" * 64,
        "approved_implementation_sha": spec.approved_implementation_sha,
        "protocol_v7_sha": spec.protocol_v7_sha,
        "seal_v2_sha": spec.seal_v2_sha,
        "label_scientific_sha": spec.label_scientific_sha,
        "runtime_v3_identity": spec.runtime_v3_identity,
        "runtime_v3_pin_sha": spec.runtime_v3_pin_sha
    }


def _build_fake_160_specs(approved_sha="a"*40) -> List[JobSpec]:
    conditions = ["mu_D", "mu_T", "B_daS", "B_perm"]
    budgets = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    seeds = [1729, 2718, 31415, 65537, 104729]
    specs = []
    for c in conditions:
        for b in budgets:
            for s in seeds:
                specs.append(_make_fake_job_spec(c, b, s, approved_sha))
    assert len(specs) == 160
    return specs


# ==============================================================================
# 18. RESUMPTION SELF-TESTS (SCENARIOS A - P)
# ==============================================================================

def test_scenario_a_fresh_empty_directory(tmp_path):
    """Scenario A: Fresh empty result directory -> all expected fake jobs execute and seal."""
    result_dir = str(tmp_path / "results_a")
    specs = _build_fake_160_specs()[:4]
    
    existing = scan_and_validate_results_directory(result_dir, specs)
    assert len(existing) == 0
    
    for spec in specs:
        res = _make_fake_worker_result(spec)
        envelope = make_sealed_worker_result(spec, res)
        save_sealed_worker_result(result_dir, spec, envelope)
        
    scanned = scan_and_validate_results_directory(result_dir, specs)
    assert len(scanned) == 4


def test_scenario_b_and_c_interrupt_and_restart(tmp_path):
    """
    Scenario B: Interrupt after N successful fake jobs -> N seals survive.
    Scenario C: Restart -> N valid seals are reused and only missing jobs execute.
    """
    result_dir = str(tmp_path / "results_bc")
    specs = _build_fake_160_specs()[:6]
    
    # Run first 3 jobs
    for spec in specs[:3]:
        res = _make_fake_worker_result(spec)
        envelope = make_sealed_worker_result(spec, res)
        save_sealed_worker_result(result_dir, spec, envelope)
        
    # Scenario B: 3 survive
    existing = scan_and_validate_results_directory(result_dir, specs)
    assert len(existing) == 3
    
    # Scenario C: Calculate missing jobs
    missing = [s for s in specs if (s.condition, s.nominal_budget, s.seed) not in existing]
    assert len(missing) == 3
    assert [s.seed for s in missing] == [s.seed for s in specs[3:]]
    
    # Execute only missing
    for spec in missing:
        res = _make_fake_worker_result(spec)
        envelope = make_sealed_worker_result(spec, res)
        save_sealed_worker_result(result_dir, spec, envelope)
        
    final_scanned = scan_and_validate_results_directory(result_dir, specs)
    assert len(final_scanned) == 6


def test_scenario_d_corrupt_sealed_payload(tmp_path):
    """Scenario D: Corrupt one sealed payload -> startup fails closed."""
    result_dir = str(tmp_path / "results_d")
    specs = _build_fake_160_specs()[:2]
    
    res = _make_fake_worker_result(specs[0])
    envelope = make_sealed_worker_result(specs[0], res)
    final_path = save_sealed_worker_result(result_dir, specs[0], envelope)
    
    with open(final_path, "w") as f:
        f.write("CORRUPT_NOT_JSON{")
        
    with pytest.raises(ValueError, match="Corrupt or unparseable"):
        scan_and_validate_results_directory(result_dir, specs)


def test_scenario_e_modify_payload_without_matching_hash(tmp_path):
    """Scenario E: Modify payload without matching hash -> fails closed."""
    result_dir = str(tmp_path / "results_e")
    specs = _build_fake_160_specs()[:2]
    
    res = _make_fake_worker_result(specs[0])
    envelope = make_sealed_worker_result(specs[0], res)
    final_path = save_sealed_worker_result(result_dir, specs[0], envelope)
    
    with open(final_path, "r") as f:
        data = json.load(f)
    data["payload"]["best_epoch"] = 999
    with open(final_path, "w") as f:
        json.dump(data, f)
        
    with pytest.raises(ValueError, match="Envelope payload SHA256 mismatch"):
        scan_and_validate_results_directory(result_dir, specs)


def test_scenario_f_wrong_implementation_sha(tmp_path):
    """Scenario F: Wrong implementation SHA -> fails closed."""
    result_dir = str(tmp_path / "results_f")
    specs = _build_fake_160_specs()[:2]
    
    res = _make_fake_worker_result(specs[0])
    envelope = make_sealed_worker_result(specs[0], res)
    envelope["approved_implementation_sha"] = "0" * 40
    
    save_sealed_worker_result(result_dir, specs[0], envelope)
    with pytest.raises(ValueError, match="Envelope approved_implementation_sha mismatch"):
        scan_and_validate_results_directory(result_dir, specs)


def test_scenario_g_wrong_protocol_sha(tmp_path):
    """Scenario G: Wrong protocol SHA -> fails closed."""
    result_dir = str(tmp_path / "results_g")
    specs = _build_fake_160_specs()[:2]
    
    res = _make_fake_worker_result(specs[0])
    envelope = make_sealed_worker_result(specs[0], res)
    envelope["protocol_v7_sha"] = "0" * 64
    
    save_sealed_worker_result(result_dir, specs[0], envelope)
    with pytest.raises(ValueError, match="Envelope protocol_v7_sha mismatch"):
        scan_and_validate_results_directory(result_dir, specs)


def test_scenario_h_wrong_label_sha(tmp_path):
    """Scenario H: Wrong label SHA -> fails closed."""
    result_dir = str(tmp_path / "results_h")
    specs = _build_fake_160_specs()[:2]
    
    res = _make_fake_worker_result(specs[0])
    envelope = make_sealed_worker_result(specs[0], res)
    envelope["label_scientific_sha"] = "0" * 64
    
    save_sealed_worker_result(result_dir, specs[0], envelope)
    with pytest.raises(ValueError, match="Envelope label_scientific_sha mismatch"):
        scan_and_validate_results_directory(result_dir, specs)


def test_scenario_i_wrong_runtime_identity_or_pin(tmp_path):
    """Scenario I: Wrong runtime identity/pin -> fails closed."""
    result_dir = str(tmp_path / "results_i")
    specs = _build_fake_160_specs()[:2]
    
    res = _make_fake_worker_result(specs[0])
    envelope = make_sealed_worker_result(specs[0], res)
    envelope["runtime_v3_identity"] = "WRONG_RUNTIME"
    
    save_sealed_worker_result(result_dir, specs[0], envelope)
    with pytest.raises(ValueError, match="Envelope runtime_v3_identity mismatch"):
        scan_and_validate_results_directory(result_dir, specs)


def test_scenario_j_wrong_population_digest(tmp_path):
    """Scenario J: Wrong population digest -> fails closed."""
    result_dir = str(tmp_path / "results_j")
    specs = _build_fake_160_specs()[:2]
    
    res = _make_fake_worker_result(specs[0])
    envelope = make_sealed_worker_result(specs[0], res)
    envelope["nominal_root_population_digest"] = "WRONG_DIGEST"
    
    save_sealed_worker_result(result_dir, specs[0], envelope)
    with pytest.raises(ValueError, match="Envelope nominal_root_population_digest mismatch"):
        scan_and_validate_results_directory(result_dir, specs)


def test_scenario_k_unexpected_tuple(tmp_path):
    """Scenario K: Unexpected tuple -> fails closed."""
    result_dir = str(tmp_path / "results_k")
    specs = _build_fake_160_specs()[:2]
    os.makedirs(result_dir, exist_ok=True)
    
    foreign_path = os.path.join(result_dir, "worker_result_FOREIGN_b999_s999.json")
    with open(foreign_path, "w") as f:
        f.write("{}")
        
    with pytest.raises(ValueError, match="Foreign, partial, or unexpected file"):
        scan_and_validate_results_directory(result_dir, specs)


def test_scenario_l_duplicate_logical_tuple(tmp_path):
    """Scenario L: Duplicate logical tuple -> fails closed."""
    specs = _build_fake_160_specs()[:2]
    duplicate_specs = [specs[0], specs[0]]
    with pytest.raises(ValueError, match="incompleteness or duplicates"):
        res = _make_fake_worker_result(specs[0])
        validate_completed_worker_results(duplicate_specs, [res, res])


def test_scenario_m_leftover_partial_temp_artifact(tmp_path):
    """Scenario M: Leftover partial/temp artifact -> explicit fail-closed policy."""
    result_dir = str(tmp_path / "results_m")
    specs = _build_fake_160_specs()[:2]
    os.makedirs(result_dir, exist_ok=True)
    
    temp_path = os.path.join(result_dir, ".tmp_worker_result_mu_D_b250_s1729.json_12345")
    with open(temp_path, "w") as f:
        f.write("partial")
        
    with pytest.raises(ValueError, match="Foreign, partial, or unexpected file in result directory: .tmp"):
        scan_and_validate_results_directory(result_dir, specs)


def test_scenario_n_no_silent_overwrite(tmp_path):
    """Scenario N: Existing valid final file cannot be silently overwritten."""
    result_dir = str(tmp_path / "results_n")
    specs = _build_fake_160_specs()[:1]
    
    res = _make_fake_worker_result(specs[0])
    envelope = make_sealed_worker_result(specs[0], res)
    save_sealed_worker_result(result_dir, specs[0], envelope)
    
    with pytest.raises(ValueError, match="Refusing to overwrite existing result file"):
        save_sealed_worker_result(result_dir, specs[0], envelope)


def test_scenario_o_finalization_with_159_results():
    """Scenario O: Finalization with 159 results -> fails."""
    specs = _build_fake_160_specs()
    results = [_make_fake_worker_result(s) for s in specs[:159]]
    
    with pytest.raises(ValueError, match="Expected 160 results, got 159"):
        validate_completed_worker_results(specs, results)


def test_scenario_p_finalization_with_exact_160_valid_results():
    """Scenario P: Finalization with exact 160 valid results -> passes."""
    specs = _build_fake_160_specs()
    results = [_make_fake_worker_result(s) for s in specs]
    
    verdict = validate_completed_worker_results(specs, results)
    assert verdict == "PASS"


# ==============================================================================
# 20. AUTHORIZATION GATES TESTS
# ==============================================================================

def test_authorization_gates_fail_closed(monkeypatch):
    """Verify that both training and analysis gates strictly fail closed."""
    # Training gate
    for val in [None, "", "1", "TRUE", "AUTHORIZED", "CHESSHEAT_REAL_TRAINING_AUTHORIZED"]:
        if val is None:
            monkeypatch.delenv("CHESSHEAT_REAL_TRAINING_AUTHORIZED", raising=False)
        else:
            monkeypatch.setenv("CHESSHEAT_REAL_TRAINING_AUTHORIZED", val)
            
        with pytest.raises(ValueError, match="Real training not authorized"):
            check_real_training_authorization()
            
    # Analysis gate
    for val in [None, "", "1", "TRUE", "AUTHORIZED", "CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED"]:
        if val is None:
            monkeypatch.delenv("CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED", raising=False)
        else:
            monkeypatch.setenv("CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED", val)
            
        with pytest.raises(ValueError, match="Scientific analysis not authorized"):
            check_analysis_authorization()


# ==============================================================================
# 21. FOUR-CONDITION INFORMATION BOUNDARY TESTS
# ==============================================================================

def test_four_condition_spatial_channel_boundaries():
    """Verify four-condition representations are strictly bound to specification."""
    from chessheat.protocol_freeze import SourcePairFeatures, build_m_d, build_m_t, build_m_zero, build_m_perm
    
    pf = SourcePairFeatures("e2e4", 100, "e7e5", -50)
    
    m_d = build_m_d(pf)
    m_t = build_m_t(pf)
    m_zero = build_m_zero()
    m_perm = build_m_perm(pf)
    
    assert len(m_d.values) == 64
    assert len(m_t.values) == 64
    assert len(m_zero.values) == 64
    assert len(m_perm.values) == 64
    
    assert all(v == 0.0 for v in m_zero.values)
    assert set(m_perm.values) == set(m_t.values)
    
    # Permutation is deterministic
    m_perm_2 = build_m_perm(pf)
    assert m_perm.values == m_perm_2.values
