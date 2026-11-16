import os
import json
import math
import hashlib
import concurrent.futures
import pytest
from typing import List, Dict

import chessheat.cp_representation_efficiency as cp
from chessheat.cp_representation_efficiency import (
    JobSpec,
    validate_worker_result,
    make_sealed_worker_result,
    save_sealed_worker_result,
    validate_sealed_worker_result,
    scan_and_validate_results_directory,
    validate_completed_worker_results,
    run_training_parent,
    check_real_training_authorization,
    check_analysis_authorization
)


def _make_valid_job_spec(condition="mu_D", budget=250, seed=1729, approved_sha="a"*40) -> JobSpec:
    test_rids = tuple(f"CHESSHEAT_TARGET_ROOT_test{i:04d}" for i in range(5))
    nom_digest = hashlib.sha256(f"nom_{condition}_{budget}_{seed}".encode()).hexdigest()
    eff_digest = hashlib.sha256(f"eff_{condition}_{budget}_{seed}".encode()).hexdigest()
    return JobSpec(
        condition=condition,
        nominal_budget=budget,
        seed=seed,
        nominal_root_ids=tuple(f"r{i}" for i in range(budget)),
        nominal_root_population_digest=nom_digest,
        validation_root_ids=tuple(f"v{i}" for i in range(5)),
        validation_population_digest=hashlib.sha256(b"vd_const").hexdigest(),
        test_root_ids=test_rids,
        test_population_digest=hashlib.sha256(b"td_const").hexdigest(),
        protocol_v7_sha="ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef",
        seal_v2_sha="2e4735f40124f4eb7017ff816a4ea55e9f72ac559236a6077a0104273b1ab9c4",
        label_scientific_sha="c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2",
        runtime_v3_identity="CHESSHEAT_ML_RUNTIME_V3",
        runtime_v3_pin_sha="e69ae6bcbf96a327b021665b5ac21b63c269cd821be84d567867058b09e98932",
        approved_implementation_sha=approved_sha,
        cache_path="dummy_cache_path",
        effective_root_population_digest=eff_digest
    )


def _make_valid_worker_result(spec: JobSpec) -> Dict:
    test_losses = {rid: 0.5 for rid in spec.test_root_ids}
    eff_digest = spec.effective_root_population_digest or hashlib.sha256(spec.nominal_root_population_digest.encode()).hexdigest()
    return {
        "schema": "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V14",
        "condition": spec.condition,
        "nominal_budget": spec.nominal_budget,
        "seed": spec.seed,
        "nominal_root_count": spec.nominal_budget,
        "nominal_root_population_digest": spec.nominal_root_population_digest,
        "effective_training_root_count": spec.nominal_budget,
        "effective_root_population_digest": eff_digest,
        "validation_population_digest": spec.validation_population_digest,
        "test_population_digest": spec.test_population_digest,
        "best_epoch": 5,
        "best_validation_root_nll": 0.45,
        "epochs_completed": 10,
        "validation_trace": [0.60, 0.55, 0.50, 0.48, 0.45, 0.46, 0.47, 0.48, 0.49, 0.50],
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
                specs.append(_make_valid_job_spec(c, b, s, approved_sha))
    assert len(specs) == 160
    return specs


# Top-level functions for multiprocessing spawn compatibility
def _mock_crashing_worker(spec: JobSpec) -> Dict:
    count_file = os.environ.get("CHESSHEAT_TEST_COUNT_FILE")
    if count_file and os.path.exists(count_file):
        with open(count_file, "r") as f:
            count = int(f.read().strip())
        count += 1
        with open(count_file, "w") as f:
            f.write(str(count))
        if count > 10:
            raise RuntimeError("SIMULATED_WORKER_CRASH_AFTER_10_JOBS")
    return _make_valid_worker_result(spec)


def _mock_completing_worker(spec: JobSpec) -> Dict:
    count_file = os.environ.get("CHESSHEAT_TEST_COMPLETING_COUNT_FILE")
    if count_file and os.path.exists(count_file):
        with open(count_file, "r") as f:
            count = int(f.read().strip())
        count += 1
        with open(count_file, "w") as f:
            f.write(str(count))
    return _make_valid_worker_result(spec)

def test_validate_worker_result_valid_positive_control():
    spec = _make_valid_job_spec()
    res = _make_valid_worker_result(spec)
    assert validate_worker_result(spec, res) == res


def test_validate_worker_result_missing_test_root_losses():
    spec = _make_valid_job_spec()
    res = _make_valid_worker_result(spec)
    del res["test_root_losses"]
    with pytest.raises(ValueError, match="test_root_losses"):
        validate_worker_result(spec, res)


def test_validate_worker_result_incomplete_test_root_losses():
    spec = _make_valid_job_spec()
    res = _make_valid_worker_result(spec)
    # Remove one test root loss
    del res["test_root_losses"][spec.test_root_ids[0]]
    with pytest.raises(ValueError, match="keys do not exactly match test_root_ids"):
        validate_worker_result(spec, res)


def test_validate_worker_result_extra_test_root_losses():
    spec = _make_valid_job_spec()
    res = _make_valid_worker_result(spec)
    res["test_root_losses"]["EXTRA_ROOT_ID"] = 0.5
    with pytest.raises(ValueError, match="keys do not exactly match test_root_ids"):
        validate_worker_result(spec, res)


def test_validate_worker_result_non_finite_test_loss():
    spec = _make_valid_job_spec()
    
    # NaN
    res_nan = _make_valid_worker_result(spec)
    res_nan["test_root_losses"][spec.test_root_ids[0]] = float('nan')
    with pytest.raises(ValueError, match="non-finite or negative"):
        validate_worker_result(spec, res_nan)
        
    # Inf
    res_inf = _make_valid_worker_result(spec)
    res_inf["test_root_losses"][spec.test_root_ids[0]] = float('inf')
    with pytest.raises(ValueError, match="non-finite or negative"):
        validate_worker_result(spec, res_inf)
        
    # Negative
    res_neg = _make_valid_worker_result(spec)
    res_neg["test_root_losses"][spec.test_root_ids[0]] = -0.01
    with pytest.raises(ValueError, match="non-finite or negative"):
        validate_worker_result(spec, res_neg)


def test_validate_worker_result_effective_root_population_digest_hostile():
    spec = _make_valid_job_spec()
    
    # Non-hex string
    res_bad = _make_valid_worker_result(spec)
    res_bad["effective_root_population_digest"] = "not_a_hex_digest"
    with pytest.raises(ValueError, match="effective_root_population_digest invalid"):
        validate_worker_result(spec, res_bad)
        
    # Wrong length
    res_short = _make_valid_worker_result(spec)
    res_short["effective_root_population_digest"] = "f" * 63
    with pytest.raises(ValueError, match="effective_root_population_digest invalid"):
        validate_worker_result(spec, res_short)
        
    # Mismatched against spec
    res_mismatch = _make_valid_worker_result(spec)
    res_mismatch["effective_root_population_digest"] = "0" * 64
    with pytest.raises(ValueError, match="effective_root_population_digest mismatch"):
        validate_worker_result(spec, res_mismatch)


def test_validate_worker_result_effective_root_count_bounds():
    spec = _make_valid_job_spec(budget=250)
    
    res_neg = _make_valid_worker_result(spec)
    res_neg["effective_training_root_count"] = -1
    with pytest.raises(ValueError, match="effective_training_root_count bounds error"):
        validate_worker_result(spec, res_neg)
        
    res_over = _make_valid_worker_result(spec)
    res_over["effective_training_root_count"] = 251
    with pytest.raises(ValueError, match="effective_training_root_count bounds error"):
        validate_worker_result(spec, res_over)


def test_validate_worker_result_malformed_canonical_model_state_sha():
    spec = _make_valid_job_spec()
    
    res_bad = _make_valid_worker_result(spec)
    res_bad["canonical_model_state_sha"] = "short_hash"
    with pytest.raises(ValueError, match="canonical_model_state_sha invalid"):
        validate_worker_result(spec, res_bad)
        
    res_nonhex = _make_valid_worker_result(spec)
    res_nonhex["canonical_model_state_sha"] = "z" * 64
    with pytest.raises(ValueError, match="canonical_model_state_sha invalid"):
        validate_worker_result(spec, res_nonhex)


def test_validate_worker_result_validation_trace_and_epochs():
    spec = _make_valid_job_spec()
    
    # Missing validation_trace
    res_no_trace = _make_valid_worker_result(spec)
    del res_no_trace["validation_trace"]
    with pytest.raises(ValueError, match="validation_trace length"):
        validate_worker_result(spec, res_no_trace)
        
    # Length mismatch
    res_len_mismatch = _make_valid_worker_result(spec)
    res_len_mismatch["validation_trace"] = [0.5, 0.4]  # len 2 vs epochs 10
    with pytest.raises(ValueError, match="inconsistent with epochs_completed"):
        validate_worker_result(spec, res_len_mismatch)
        
    # Non-finite entry
    res_nan = _make_valid_worker_result(spec)
    res_nan["validation_trace"][0] = float('nan')
    with pytest.raises(ValueError, match="validation_trace.*non-finite"):
        validate_worker_result(spec, res_nan)
        
    # Negative entry
    res_neg = _make_valid_worker_result(spec)
    res_neg["validation_trace"][0] = -0.1
    with pytest.raises(ValueError, match="validation_trace.*non-finite or negative"):
        validate_worker_result(spec, res_neg)


def test_validate_worker_result_best_epoch_bounds():
    spec = _make_valid_job_spec()
    
    res_zero = _make_valid_worker_result(spec)
    res_zero["best_epoch"] = 0
    with pytest.raises(ValueError, match="best_epoch bounds error"):
        validate_worker_result(spec, res_zero)
        
    res_over = _make_valid_worker_result(spec)
    res_over["best_epoch"] = 11  # epochs_completed is 10
    with pytest.raises(ValueError, match="best_epoch bounds error"):
        validate_worker_result(spec, res_over)


def test_validate_worker_result_earliest_minimum_rule():
    spec = _make_valid_job_spec()
    
    # best_validation_root_nll does not match min(val_trace)
    res_nll_mismatch = _make_valid_worker_result(spec)
    res_nll_mismatch["best_validation_root_nll"] = 0.40  # min is 0.45
    with pytest.raises(ValueError, match="best_validation_root_nll.*!= min"):
        validate_worker_result(spec, res_nll_mismatch)
        
    # Ties in validation_trace: epoch 2 and epoch 4 both have 0.45, epoch 2 is earliest
    # Setting best_epoch to 4 must be rejected under earliest-minimum rule
    res_tie = _make_valid_worker_result(spec)
    res_tie["validation_trace"] = [0.60, 0.45, 0.50, 0.45, 0.46, 0.47, 0.48, 0.49, 0.50, 0.51]
    res_tie["best_validation_root_nll"] = 0.45
    res_tie["best_epoch"] = 4  # Should be 2 (earliest index)
    with pytest.raises(ValueError, match="does not match earliest-minimum epoch 2"):
        validate_worker_result(spec, res_tie)
        
    # Correct earliest minimum passes
    res_tie["best_epoch"] = 2
    assert validate_worker_result(spec, res_tie) == res_tie


# ==============================================================================
# 2. DURABLE ENVELOPE PARITY & RE-HASHED HOSTILE ENVELOPES
# ==============================================================================

def test_durable_seal_rejects_rehashed_hostile_payloads():
    """Any defect in payload is caught on resumption EVEN IF envelope is re-hashed with matching SHA."""
    spec = _make_valid_job_spec()
    
    # 1. Missing test_root_losses, re-hashed
    bad_payload = _make_valid_worker_result(spec)
    del bad_payload["test_root_losses"]
    env1 = make_sealed_worker_result(spec, bad_payload)
    with pytest.raises(ValueError, match="test_root_losses"):
        validate_sealed_worker_result(env1, spec)
        
    # 2. Incomplete test_root_losses, re-hashed
    bad_payload = _make_valid_worker_result(spec)
    del bad_payload["test_root_losses"][spec.test_root_ids[0]]
    env2 = make_sealed_worker_result(spec, bad_payload)
    with pytest.raises(ValueError, match="keys do not exactly match test_root_ids"):
        validate_sealed_worker_result(env2, spec)
        
    # 3. Negative / non-finite test loss, re-hashed
    bad_payload = _make_valid_worker_result(spec)
    bad_payload["test_root_losses"][spec.test_root_ids[0]] = -0.01
    env3 = make_sealed_worker_result(spec, bad_payload)
    with pytest.raises(ValueError, match="non-finite or negative"):
        validate_sealed_worker_result(env3, spec)
        
    # 4. Inconsistent validation trace length, re-hashed
    bad_payload = _make_valid_worker_result(spec)
    bad_payload["validation_trace"] = [0.5]
    env4 = make_sealed_worker_result(spec, bad_payload)
    with pytest.raises(ValueError, match="inconsistent with epochs_completed"):
        validate_sealed_worker_result(env4, spec)
        
    # 5. Best epoch outside executed range, re-hashed
    bad_payload = _make_valid_worker_result(spec)
    bad_payload["best_epoch"] = 99
    env5 = make_sealed_worker_result(spec, bad_payload)
    with pytest.raises(ValueError, match="best_epoch bounds error"):
        validate_sealed_worker_result(env5, spec)
        
    # 6. Best validation NLL inconsistent with earliest-minimum rule, re-hashed
    bad_payload = _make_valid_worker_result(spec)
    bad_payload["best_validation_root_nll"] = 0.99
    env6 = make_sealed_worker_result(spec, bad_payload)
    with pytest.raises(ValueError, match="best_validation_root_nll.*!= min"):
        validate_sealed_worker_result(env6, spec)


# ==============================================================================
# 3. ATOMIC NO-CLOBBER PUBLICATION & CONCURRENCY
# ==============================================================================

def test_atomic_no_clobber_sequential_rejected(tmp_path):
    result_dir = str(tmp_path / "atomic_seq")
    spec = _make_valid_job_spec()
    res = _make_valid_worker_result(spec)
    env = make_sealed_worker_result(spec, res)
    
    path1 = save_sealed_worker_result(result_dir, spec, env)
    assert os.path.exists(path1)
    
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        save_sealed_worker_result(result_dir, spec, env)


def test_atomic_no_clobber_concurrent_race(tmp_path):
    result_dir = str(tmp_path / "atomic_race")
    spec = _make_valid_job_spec()
    
    # Pre-generate 10 different payloads with varying seeds/shas for race
    envelopes = []
    for i in range(10):
        res = _make_valid_worker_result(spec)
        res["canonical_model_state_sha"] = f"{i:x}" * 64
        envelopes.append(make_sealed_worker_result(spec, res))
        
    def publish_task(idx):
        try:
            p = save_sealed_worker_result(result_dir, spec, envelopes[idx])
            return ("SUCCESS", idx, p)
        except ValueError as e:
            return ("CLOBBER_PREVENTED", idx, str(e))
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futs = [executor.submit(publish_task, i) for i in range(10)]
        outcomes = [f.result() for f in concurrent.futures.as_completed(futs)]
        
    successes = [o for o in outcomes if o[0] == "SUCCESS"]
    clobbers = [o for o in outcomes if o[0] == "CLOBBER_PREVENTED"]
    
    assert len(successes) == 1, f"Expected exactly 1 winner, got {len(successes)}"
    assert len(clobbers) == 9, f"Expected exactly 9 clobbers prevented, got {len(clobbers)}"
    
    # Directory check: exactly 1 file exists, zero leftover .tmp_* files
    entries = os.listdir(result_dir)
    assert len(entries) == 1
    assert not any(e.startswith(".tmp") for e in entries)


# ==============================================================================
# 4. DEMONSTRATED PARENT CRASH, RESTART & MANIFEST INTEGRATION
# ==============================================================================

def test_parent_interruption_restart_complete_manifest(tmp_path, monkeypatch):
    """
    Hostile parent integration test:
    1. Interruption after 10 jobs during run_training_parent.
    2. Exactly 10 durable valid files exist, zero partial artifacts.
    3. Restart in fresh parent context: reuses 10 valid results, computes only missing 150.
    4. All 160 jobs validated and finalized.
    5. Second restart: executes 0 jobs, immediate finalization.
    """
    result_dir = str(tmp_path / "parent_run")
    specs = _build_fake_160_specs()
    
    # Mock environment and cache to run parent integration without Stockfish / real training
    monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", "a"*40)
    monkeypatch.setenv("CHESSHEAT_REAL_TRAINING_AUTHORIZED", "CHESSHEAT_REAL_TRAINING_V1_AUTHORIZED")
    
    # Mock verify_approved_sha_gate and verify_training_evidence_preflight
    monkeypatch.setattr(cp, "verify_approved_sha_gate", lambda sha, root: None)
    
    from chessheat.cp_representation_efficiency import EvidenceIdentity
    ev_id = EvidenceIdentity(
        protocol_v7_sha="ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef",
        seal_v2_sha="2e4735f40124f4eb7017ff816a4ea55e9f72ac559236a6077a0104273b1ab9c4",
        runtime_v3_pin_sha="e69ae6bcbf96a327b021665b5ac21b63c269cd821be84d567867058b09e98932",
        runtime_v3_package_lock_sha="a"*64,
        runtime_v3_code_lock_sha="a"*64,
        runtime_v3_requirements_sha="a"*64,
        target_label_runtime_pin_sha="a"*64,
        target_label_requirements_sha="a"*64,
        evidence_audit_commit="a"*40,
        evidence_supplement_commit="a"*40,
        label_scientific_sha="c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2",
        label_compressed_sha="a"*64
    )
    monkeypatch.setattr(cp, "verify_training_evidence_preflight", lambda sha, root: ev_id)
    
    # Mock DerivedCache and populations to return fake 160 specs
    class DummyCache:
        def __init__(self, *args): pass
    monkeypatch.setattr(cp, "DerivedCache", DummyCache)
    monkeypatch.setattr(cp, "build_frozen_populations", lambda cache: None)
    monkeypatch.setattr(cp, "build_job_specs", lambda pops, ev, path, sha: specs)
    
    # Phase 1: Worker crashes on the 11th job
    crash_count_file = str(tmp_path / "crash_count.txt")
    with open(crash_count_file, "w") as f:
        f.write("0")
    monkeypatch.setenv("CHESSHEAT_TEST_COUNT_FILE", crash_count_file)
        
    with pytest.raises(RuntimeError, match="SIMULATED_WORKER_CRASH_AFTER_10_JOBS"):
        run_training_parent(
            approved_sha="a"*40,
            cache_path="dummy",
            cache_sha=ev_id.label_scientific_sha,
            result_dir=result_dir,
            worker_fn=_mock_crashing_worker
        )
        
    # Verify disk state after crash
    files = [f for f in os.listdir(result_dir) if f.endswith(".json")]
    assert len(files) == 10, f"Expected 10 files saved before crash, got {len(files)}"
    assert not any(f.startswith(".tmp") for f in os.listdir(result_dir)), "No partial tmp files should remain"
    
    # Phase 2: Restart in fresh context with completing worker
    completing_count_file = str(tmp_path / "completing_count.txt")
    with open(completing_count_file, "w") as f:
        f.write("0")
    monkeypatch.setenv("CHESSHEAT_TEST_COMPLETING_COUNT_FILE", completing_count_file)
        
    verdict = run_training_parent(
        approved_sha="a"*40,
        cache_path="dummy",
        cache_sha=ev_id.label_scientific_sha,
        result_dir=result_dir,
        worker_fn=_mock_completing_worker
    )
    
    assert verdict == "STOP_BEFORE_SCIENTIFIC_ANALYSIS"
    # Crucial assertion: exactly 150 jobs were computed on restart (160 - 10 reused)
    with open(completing_count_file, "r") as f:
        completed_count = int(f.read().strip())
    assert completed_count == 150, f"Expected 150 missing jobs executed, got {completed_count}"
    
    # Verify disk state after completion: exactly 160 sealed files
    all_files = [f for f in os.listdir(result_dir) if f.endswith(".json")]
    assert len(all_files) == 160
    
    # Phase 3: Second restart on fully completed directory -> executes 0 jobs
    with open(completing_count_file, "w") as f:
        f.write("0")
        
    verdict_subsequent = run_training_parent(
        approved_sha="a"*40,
        cache_path="dummy",
        cache_sha=ev_id.label_scientific_sha,
        result_dir=result_dir,
        worker_fn=_mock_completing_worker
    )
    assert verdict_subsequent == "STOP_BEFORE_SCIENTIFIC_ANALYSIS"
    with open(completing_count_file, "r") as f:
        zero_count = int(f.read().strip())
    assert zero_count == 0, "Subsequent rerun must execute 0 jobs"
    
    # Phase 4: Tamper with one file on disk -> parent fails closed on startup
    corrupt_file = os.path.join(result_dir, all_files[0])
    with open(corrupt_file, "r") as f:
        data = json.load(f)
    data["payload"]["best_epoch"] = 999  # Invalid
    # Re-hash payload to simulate hostile re-hash tampering
    p_str = json.dumps(data["payload"], sort_keys=True, separators=(',', ':'))
    data["payload_sha256"] = hashlib.sha256(p_str.encode()).hexdigest()
    with open(corrupt_file, "w") as f:
        json.dump(data, f)
        
    with pytest.raises(ValueError, match="best_epoch bounds error"):
        run_training_parent(
            approved_sha="a"*40,
            cache_path="dummy",
            cache_sha=ev_id.label_scientific_sha,
            result_dir=result_dir,
            worker_fn=_mock_completing_worker
        )
