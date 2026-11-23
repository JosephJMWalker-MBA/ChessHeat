import os
import json
import math
import hashlib
import subprocess
import pytest
from typing import List, Dict

import chessheat.cp_representation_efficiency as cp
from chessheat.cp_representation_efficiency import (
    JobSpec,
    EvidenceIdentity,
    verify_training_evidence_preflight,
    verify_replication_training_evidence_preflight,
    validate_worker_result,
    make_sealed_worker_result,
    save_sealed_worker_result,
    validate_sealed_worker_result,
    scan_and_validate_results_directory,
    validate_completed_worker_results,
    build_job_specs,
    run_training_parent
)

REPLICATION_EVIDENCE_COMMIT = "732ba450f47511d0f93af0dcaef924b2f2a57f89"
REPLICATION_DERIVATION_COMMIT = "14b85055fd439cf7f905adf51718544485b1ac17"
HISTORICAL_AUDIT_COMMIT = "2f7560a38427754404c6f1ee6115db950d18815c"
HISTORICAL_SUPPLEMENT_COMMIT = "87e1edad72d2899d0bc7a05d11d9601d60b7cba3"

REPLICATION_SOURCE_SHA = "9cfe28a13f185e207ac42c5708597b0577ef93f4fce29ca482e4e6a9c8d83774"
REPLICATION_TARGET_SHA = "d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00"
REPLICATION_CACHE_SHA = "1b148d07c1cad975b5d21233cd7b384493a61a666cdec06b4e733b82379afba3"
REPLICATION_SEAL_SHA = "c2457bb1531856b0e2b235a69dd2b7b77b64e2419032cf6616cffe6a96b2baa8"
REPLICATION_COMPRESSED_SHA = "5ab9d94e5806b19721879962f15e5ecd1763cdb0380c85337571af6596a3a61e"
REPLICATION_MANIFEST_SHA = "5a013e64265820b65d1d3687fcee98aa607ab41470294d11df7b2f803c8e063d"
PROTOCOL_V7_SHA = "ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef"

V6_LABEL_SCIENTIFIC_SHA = "c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2"
V6_SEAL_V2_SHA = "2e4735f40124f4eb7017ff816a4ea55e9f72ac559236a6077a0104273b1ab9c4"


def _make_replication_job_spec(condition="mu_D", budget=250, seed=1729, approved_sha=REPLICATION_EVIDENCE_COMMIT) -> JobSpec:
    test_rids = tuple(f"CHESSHEAT_TARGET_ROOT_test{i:04d}" for i in range(5))
    nom_digest = hashlib.sha256(f"nom_rep_{condition}_{budget}_{seed}".encode()).hexdigest()
    eff_digest = hashlib.sha256(f"eff_rep_{condition}_{budget}_{seed}".encode()).hexdigest()
    return JobSpec(
        condition=condition,
        nominal_budget=budget,
        seed=seed,
        nominal_root_ids=tuple(f"r{i}" for i in range(budget)),
        nominal_root_population_digest=nom_digest,
        validation_root_ids=tuple(f"v{i}" for i in range(5)),
        validation_population_digest=hashlib.sha256(b"vd_rep").hexdigest(),
        test_root_ids=test_rids,
        test_population_digest=hashlib.sha256(b"td_rep").hexdigest(),
        protocol_v7_sha=PROTOCOL_V7_SHA,
        seal_v2_sha=None,
        label_scientific_sha=REPLICATION_CACHE_SHA,
        runtime_v3_identity="CHESSHEAT_ML_RUNTIME_V3",
        runtime_v3_pin_sha="e69ae6bcbf96a327b021665b5ac21b63c269cd821be84d567867058b09e98932",
        approved_implementation_sha=approved_sha,
        cache_path="dummy_rep1_cache_path",
        effective_root_population_digest=eff_digest,
        lineage="V7_REPLICATION_1",
        replication_seal_sha=REPLICATION_SEAL_SHA
    )


def _make_v6_job_spec(condition="mu_D", budget=250, seed=1729, approved_sha="a"*40) -> JobSpec:
    test_rids = tuple(f"CHESSHEAT_TARGET_ROOT_test{i:04d}" for i in range(5))
    nom_digest = hashlib.sha256(f"nom_v6_{condition}_{budget}_{seed}".encode()).hexdigest()
    eff_digest = hashlib.sha256(f"eff_v6_{condition}_{budget}_{seed}".encode()).hexdigest()
    return JobSpec(
        condition=condition,
        nominal_budget=budget,
        seed=seed,
        nominal_root_ids=tuple(f"r{i}" for i in range(budget)),
        nominal_root_population_digest=nom_digest,
        validation_root_ids=tuple(f"v{i}" for i in range(5)),
        validation_population_digest=hashlib.sha256(b"vd_v6").hexdigest(),
        test_root_ids=test_rids,
        test_population_digest=hashlib.sha256(b"td_v6").hexdigest(),
        protocol_v7_sha=PROTOCOL_V7_SHA,
        seal_v2_sha=V6_SEAL_V2_SHA,
        label_scientific_sha=V6_LABEL_SCIENTIFIC_SHA,
        runtime_v3_identity="CHESSHEAT_ML_RUNTIME_V3",
        runtime_v3_pin_sha="e69ae6bcbf96a327b021665b5ac21b63c269cd821be84d567867058b09e98932",
        approved_implementation_sha=approved_sha,
        cache_path="dummy_v6_cache_path",
        effective_root_population_digest=eff_digest,
        lineage="V6_HISTORICAL",
        replication_seal_sha=None
    )


def _make_valid_worker_result_for_spec(spec: JobSpec) -> Dict:
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
        "replication_seal_sha": getattr(spec, "replication_seal_sha", None),
        "lineage": getattr(spec, "lineage", "V6_HISTORICAL"),
        "label_scientific_sha": spec.label_scientific_sha,
        "runtime_v3_identity": spec.runtime_v3_identity,
        "runtime_v3_pin_sha": spec.runtime_v3_pin_sha
    }


def _build_fake_160_replication_specs(approved_sha=REPLICATION_EVIDENCE_COMMIT) -> List[JobSpec]:
    conditions = ["mu_D", "mu_T", "B_daS", "B_perm"]
    budgets = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    seeds = [1729, 2718, 31415, 65537, 104729]
    specs = []
    for c in conditions:
        for b in budgets:
            for s in seeds:
                specs.append(_make_replication_job_spec(c, b, s, approved_sha))
    assert len(specs) == 160
    return specs


def _mock_crashing_worker(spec: JobSpec) -> Dict:
    count_file = os.environ.get("CHESSHEAT_TEST_REP_COUNT_FILE")
    if count_file and os.path.exists(count_file):
        with open(count_file, "r") as f:
            count = int(f.read().strip())
        count += 1
        with open(count_file, "w") as f:
            f.write(str(count))
        if count > 10:
            raise RuntimeError("SIMULATED_WORKER_CRASH_AFTER_10_JOBS")
    return _make_valid_worker_result_for_spec(spec)


def _mock_completing_worker(spec: JobSpec) -> Dict:
    count_file = os.environ.get("CHESSHEAT_TEST_REP_COMPLETING_COUNT_FILE")
    if count_file and os.path.exists(count_file):
        with open(count_file, "r") as f:
            count = int(f.read().strip())
        count += 1
        with open(count_file, "w") as f:
            f.write(str(count))
    return _make_valid_worker_result_for_spec(spec)


# --- Test 1: Positive Control on Real Repo ---

def test_replication_evidence_preflight_positive_control():
    """Verify replication preflight succeeds against repository HEAD and returns exact bindings."""
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    ev_id = verify_replication_training_evidence_preflight(current_head, repo_root=".")
    
    assert ev_id.lineage == "V7_REPLICATION_1"
    assert ev_id.seal_v2_sha is None
    assert ev_id.protocol_v7_sha == PROTOCOL_V7_SHA
    assert ev_id.replication_seal_sha == REPLICATION_SEAL_SHA
    assert ev_id.label_scientific_sha == REPLICATION_CACHE_SHA
    assert ev_id.label_compressed_sha == REPLICATION_COMPRESSED_SHA
    assert ev_id.source_raw_sha == REPLICATION_SOURCE_SHA
    assert ev_id.target_raw_sha == REPLICATION_TARGET_SHA
    assert ev_id.manifest_digest == REPLICATION_MANIFEST_SHA
    assert ev_id.derivation_implementation_commit == REPLICATION_DERIVATION_COMMIT
    assert ev_id.runtime_v3_pin_sha == "e69ae6bcbf96a327b021665b5ac21b63c269cd821be84d567867058b09e98932"


# --- Test 2: Replication Preflight Hostile Tampering Rejections ---

def test_replication_evidence_preflight_tampered_seal_content(monkeypatch):
    """Mutating any upstream evidence inside the replication seal JSON causes preflight to fail closed."""
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    seal_path = os.path.abspath("artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v7_rep1.json")
    
    import builtins
    orig_open = builtins.open
    with orig_open(seal_path, "r", encoding="utf-8") as f:
        real_seal_data = json.load(f)
    with orig_open(seal_path, "rb") as f:
        real_seal_bytes = f.read()

    for bad_field, bad_val in [
        ("source_raw_sha256", "0" * 64),
        ("target_raw_sha256", "0" * 64),
        ("manifest_decompressed_sha256", "0" * 64),
        ("decompressed_canonical_sha256", "0" * 64),
        ("compressed_sha256", "0" * 64),
        ("implementation_sha", "0" * 40),
        ("pair_eligible_root_count", 99999),
        ("source_pair_count", 99999),
        ("protocol_id", "WRONG_PROTOCOL"),
        ("label_derivation_protocol", "WRONG_DERIVATION"),
        ("schema", "WRONG_SCHEMA"),
        ("status", "UNSEALED")
    ]:
        tampered_seal = dict(real_seal_data)
        tampered_seal[bad_field] = bad_val
        
        def mock_open(path, *args, **kwargs):
            if os.path.abspath(path) == seal_path:
                import io
                mode = args[0] if args else kwargs.get("mode", "r")
                if "b" in mode:
                    return io.BytesIO(real_seal_bytes)
                else:
                    return io.StringIO(json.dumps(tampered_seal))
            return orig_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)
        with pytest.raises(ValueError, match=f"({bad_field}|mismatch|schema|status|protocol)"):
            verify_replication_training_evidence_preflight(current_head, repo_root=".")


def test_replication_evidence_preflight_tampered_seal_sha(monkeypatch):
    """If the derivation seal file has any mismatch from its expected SHA, preflight fails closed."""
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    seal_path = os.path.abspath("artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v7_rep1.json")
    
    import builtins
    orig_open = builtins.open
    def mock_open(path, *args, **kwargs):
        if os.path.abspath(path) == seal_path:
            import io
            return io.BytesIO(b"corrupted seal bytes")
        return orig_open(path, *args, **kwargs)
        
    monkeypatch.setattr(builtins, "open", mock_open)
    with pytest.raises(ValueError, match="SHA mismatch for artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v7_rep1.json"):
        verify_replication_training_evidence_preflight(current_head, repo_root=".")


def test_replication_evidence_preflight_tampered_raw_source(monkeypatch):
    """If raw source artifact on disk has mismatched SHA, preflight fails closed."""
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    raw_source = os.path.abspath("artifacts/research/cp_source_feasibility_2026_07/raw/cp_source_root_results_v2.jsonl")
    
    import builtins
    orig_open = builtins.open
    def mock_open(path, *args, **kwargs):
        if os.path.abspath(path) == raw_source:
            import io
            return io.BytesIO(b"corrupted raw source")
        return orig_open(path, *args, **kwargs)
        
    monkeypatch.setattr(builtins, "open", mock_open)
    with pytest.raises(ValueError, match="SHA mismatch for raw source artifact"):
        verify_replication_training_evidence_preflight(current_head, repo_root=".")


def test_replication_evidence_preflight_tampered_raw_target(monkeypatch):
    """If raw target artifact on disk has mismatched SHA, preflight fails closed."""
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    raw_target = os.path.abspath("artifacts/research/cp_target_acquisition_2026_07/raw/cp_target_root_results_v2.jsonl")
    
    import builtins
    orig_open = builtins.open
    def mock_open(path, *args, **kwargs):
        if os.path.abspath(path) == raw_target:
            import io
            return io.BytesIO(b"corrupted raw target")
        return orig_open(path, *args, **kwargs)
        
    monkeypatch.setattr(builtins, "open", mock_open)
    with pytest.raises(ValueError, match="SHA mismatch for raw target artifact"):
        verify_replication_training_evidence_preflight(current_head, repo_root=".")


def test_replication_evidence_preflight_non_ancestor_commit():
    """Unrelated commit without proper provenance ancestry fails closed."""
    with tempfile_commit() as unrelated_commit:
        with pytest.raises(ValueError, match="missing or not an ancestor"):
            verify_replication_training_evidence_preflight(unrelated_commit, repo_root=".")


# Helper to generate an isolated commit on an orphan branch
def tempfile_commit():
    class CommitCtx:
        def __enter__(self):
            # Create a detached dummy commit
            tree = subprocess.check_output(["git", "write-tree"]).decode().strip()
            commit = subprocess.check_output(["git", "commit-tree", tree, "-m", "orphan"]).decode().strip()
            self.commit = commit
            return commit
        def __exit__(self, *args):
            pass
    return CommitCtx()


# --- Test 3: Historical V6 Lineage Isolation ---

def test_v6_preflight_isolation():
    """Historical V6 preflight retains V6 behavior and rejects replication identity."""
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    v6_id = verify_training_evidence_preflight(current_head, repo_root=".")
    
    assert v6_id.lineage == "V6_HISTORICAL"
    assert v6_id.seal_v2_sha == V6_SEAL_V2_SHA
    assert v6_id.label_scientific_sha == V6_LABEL_SCIENTIFIC_SHA
    assert v6_id.replication_seal_sha is None


# --- Test 4: Cross-Lineage Envelope and Result Rejection ---

def test_cross_lineage_envelope_rejection():
    """Replication job spec strictly rejects V6 envelopes and vice versa."""
    rep_spec = _make_replication_job_spec()
    v6_spec = _make_v6_job_spec()
    
    rep_result = _make_valid_worker_result_for_spec(rep_spec)
    v6_result = _make_valid_worker_result_for_spec(v6_spec)
    
    rep_envelope = make_sealed_worker_result(rep_spec, rep_result)
    v6_envelope = make_sealed_worker_result(v6_spec, v6_result)
    
    # 1. Positive controls
    assert validate_sealed_worker_result(rep_envelope, rep_spec) == rep_result
    assert validate_sealed_worker_result(v6_envelope, v6_spec) == v6_result
    
    # 2. Cross-lineage rejection
    with pytest.raises(ValueError, match="Envelope lineage mismatch: expected V7_REPLICATION_1, got V6_HISTORICAL"):
        validate_sealed_worker_result(v6_envelope, rep_spec)
        
    with pytest.raises(ValueError, match="Envelope lineage mismatch: expected V6_HISTORICAL, got V7_REPLICATION_1"):
        validate_sealed_worker_result(rep_envelope, v6_spec)


def test_cross_lineage_envelope_hostile_spoofing():
    """Hostile envelope with spoofed lineage string but mismatched seal/hashes fails closed."""
    rep_spec = _make_replication_job_spec(approved_sha=REPLICATION_EVIDENCE_COMMIT)
    v6_spec = _make_v6_job_spec(approved_sha=REPLICATION_EVIDENCE_COMMIT)
    
    v6_result = _make_valid_worker_result_for_spec(v6_spec)
    v6_envelope = make_sealed_worker_result(v6_spec, v6_result)
    
    # Spoof lineage in envelope without touching payload
    spoofed = dict(v6_envelope)
    spoofed["lineage"] = "V7_REPLICATION_1"
    with pytest.raises(ValueError, match="(replication_seal_sha mismatch|seal_v2_sha mismatch|label_scientific_sha mismatch)"):
        validate_sealed_worker_result(spoofed, rep_spec)
        
    # Re-hash payload with spoofed fields in worker result
    spoofed_result = dict(v6_result)
    spoofed_result["lineage"] = "V7_REPLICATION_1"
    spoofed_result["replication_seal_sha"] = REPLICATION_SEAL_SHA
    # Still has V6 seal_v2_sha and V6 label_scientific_sha
    spoofed_envelope = make_sealed_worker_result(rep_spec, spoofed_result)
    # The payload will fail validate_worker_result because of seal_v2_sha mismatch (expected None)
    with pytest.raises(ValueError, match="(seal_v2_sha mismatch|label_scientific_sha mismatch)"):
        validate_sealed_worker_result(spoofed_envelope, rep_spec)


def test_validate_worker_result_lineage_mismatch():
    """Worker result payload lineage mismatch fails closed."""
    rep_spec = _make_replication_job_spec()
    res = _make_valid_worker_result_for_spec(rep_spec)
    res["lineage"] = "V6_HISTORICAL"
    with pytest.raises(ValueError, match="Worker result lineage mismatch"):
        validate_worker_result(rep_spec, res)


def test_validate_worker_result_replication_seal_mismatch():
    """Worker result payload replication_seal_sha mismatch fails closed."""
    rep_spec = _make_replication_job_spec()
    res = _make_valid_worker_result_for_spec(rep_spec)
    res["replication_seal_sha"] = "0" * 64
    with pytest.raises(ValueError, match="replication_seal_sha mismatch"):
        validate_worker_result(rep_spec, res)


# --- Test 5: Parent Lineage Directory and Cache Separation ---

def test_parent_refuses_cross_lineage_result_directory(tmp_path, monkeypatch):
    """Parent refuses to execute replication jobs into V6 result directory or vice versa."""
    monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", REPLICATION_EVIDENCE_COMMIT)
    monkeypatch.setenv("CHESSHEAT_REAL_TRAINING_AUTHORIZED", "CHESSHEAT_REAL_TRAINING_V1_AUTHORIZED")
    monkeypatch.setattr(cp, "verify_approved_sha_gate", lambda sha, root: None)
    
    # 1. Replication lineage into V6 directory
    with pytest.raises(ValueError, match="Refusing to reuse historical V6 result directory for replication lineage"):
        run_training_parent(
            approved_sha=REPLICATION_EVIDENCE_COMMIT,
            cache_path="dummy",
            cache_sha=REPLICATION_CACHE_SHA,
            result_dir="artifacts/research/cp_representation_efficiency_training_v1/worker_results",
            lineage="V7_REPLICATION_1"
        )
        
    # 2. V6 lineage into replication directory
    with pytest.raises(ValueError, match="Refusing to reuse replication result directory for historical V6 lineage"):
        run_training_parent(
            approved_sha=REPLICATION_EVIDENCE_COMMIT,
            cache_path="dummy",
            cache_sha=V6_LABEL_SCIENTIFIC_SHA,
            result_dir="artifacts/research/cp_representation_efficiency_training_v7_rep1/worker_results",
            lineage="V6_HISTORICAL"
        )


def test_parent_refuses_cross_lineage_cache_sha(monkeypatch):
    """Parent refuses if cache_sha does not match the active lineage's canonical scientific SHA."""
    monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", REPLICATION_EVIDENCE_COMMIT)
    monkeypatch.setenv("CHESSHEAT_REAL_TRAINING_AUTHORIZED", "CHESSHEAT_REAL_TRAINING_V1_AUTHORIZED")
    monkeypatch.setattr(cp, "verify_approved_sha_gate", lambda sha, root: None)
    
    # Passing V6 cache SHA with replication lineage
    with pytest.raises(ValueError, match="cache_sha MUST exactly equal the canonical label scientific SHA"):
        run_training_parent(
            approved_sha=REPLICATION_EVIDENCE_COMMIT,
            cache_path="dummy",
            cache_sha=V6_LABEL_SCIENTIFIC_SHA,
            lineage="V7_REPLICATION_1"
        )
        
    # Passing replication cache SHA with V6 lineage
    with pytest.raises(ValueError, match="cache_sha MUST exactly equal the canonical label scientific SHA"):
        run_training_parent(
            approved_sha=REPLICATION_EVIDENCE_COMMIT,
            cache_path="dummy",
            cache_sha=REPLICATION_CACHE_SHA,
            lineage="V6_HISTORICAL"
        )


def test_parent_refuses_unknown_lineage(monkeypatch):
    """Parent rejects unapproved lineage string."""
    monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", REPLICATION_EVIDENCE_COMMIT)
    monkeypatch.setenv("CHESSHEAT_REAL_TRAINING_AUTHORIZED", "CHESSHEAT_REAL_TRAINING_V1_AUTHORIZED")
    monkeypatch.setattr(cp, "verify_approved_sha_gate", lambda sha, root: None)
    
    with pytest.raises(ValueError, match="Unknown or unsupported lineage: V8_UNKNOWN"):
        run_training_parent(
            approved_sha=REPLICATION_EVIDENCE_COMMIT,
            cache_path="dummy",
            cache_sha="0"*64,
            lineage="V8_UNKNOWN"
        )


# --- Test 6: Frozen 160 Job Specifications Invariance ---

def test_build_job_specs_replication_invariance():
    """Verify build_job_specs produces exactly 160 specs with replication lineage and seal."""
    # Fake populations
    train_roots = [f"r{i}" for i in range(25000)]
    budgets = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    val_roots = tuple(f"v{i}" for i in range(5000))
    test_roots = tuple(f"t{i}" for i in range(5000))
    d_val = cp.canonical_root_population_digest(val_roots)
    d_test = cp.canonical_root_population_digest(test_roots)
    b_digs = {b: cp.canonical_root_population_digest(train_roots[:b]) for b in budgets}
    pops = (train_roots, budgets, val_roots, test_roots, d_val, d_test, b_digs)
    
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    ev_id = verify_replication_training_evidence_preflight(current_head, repo_root=".")
    
    specs = build_job_specs(pops, ev_id, "dummy_cache", current_head)
    assert len(specs) == 160
    
    conditions = set()
    budgets_seen = set()
    seeds_seen = set()
    
    for s in specs:
        assert s.lineage == "V7_REPLICATION_1"
        assert s.seal_v2_sha is None
        assert s.replication_seal_sha == REPLICATION_SEAL_SHA
        assert s.label_scientific_sha == REPLICATION_CACHE_SHA
        assert s.protocol_v7_sha == PROTOCOL_V7_SHA
        assert s.approved_implementation_sha == current_head
        conditions.add(s.condition)
        budgets_seen.add(s.nominal_budget)
        seeds_seen.add(s.seed)
        
    assert conditions == {"mu_D", "mu_T", "B_daS", "B_perm"}
    assert budgets_seen == {250, 500, 1000, 2000, 4000, 8000, 16000, 20000}
    assert seeds_seen == {1729, 2718, 31415, 65537, 104729}


# --- Test 7: Replication Parent Lifecycle (Crash & Resumption Integration) ---

def test_replication_parent_interruption_and_restart(tmp_path, monkeypatch):
    """
    Hostile parent integration test under V7_REPLICATION_1:
    1. Interruption after 10 jobs during run_training_parent.
    2. Exactly 10 durable valid files exist, zero partial artifacts.
    3. Restart in fresh parent context: reuses 10 valid results, computes only missing 150.
    4. All 160 jobs validated and finalized.
    5. Second restart: executes 0 jobs, immediate finalization.
    """
    result_dir = str(tmp_path / "rep1_parent_run")
    specs = _build_fake_160_replication_specs()
    
    monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", REPLICATION_EVIDENCE_COMMIT)
    monkeypatch.setenv("CHESSHEAT_REAL_TRAINING_AUTHORIZED", "CHESSHEAT_REAL_TRAINING_V1_AUTHORIZED")
    monkeypatch.setattr(cp, "verify_approved_sha_gate", lambda sha, root: None)
    
    ev_id = EvidenceIdentity(
        protocol_v7_sha=PROTOCOL_V7_SHA,
        seal_v2_sha=None,
        runtime_v3_pin_sha="e69ae6bcbf96a327b021665b5ac21b63c269cd821be84d567867058b09e98932",
        runtime_v3_package_lock_sha="a"*64,
        runtime_v3_code_lock_sha="a"*64,
        runtime_v3_requirements_sha="a"*64,
        target_label_runtime_pin_sha="a"*64,
        target_label_requirements_sha="a"*64,
        evidence_audit_commit=HISTORICAL_AUDIT_COMMIT,
        evidence_supplement_commit=HISTORICAL_SUPPLEMENT_COMMIT,
        label_scientific_sha=REPLICATION_CACHE_SHA,
        label_compressed_sha=REPLICATION_COMPRESSED_SHA,
        lineage="V7_REPLICATION_1",
        replication_seal_sha=REPLICATION_SEAL_SHA
    )
    monkeypatch.setattr(cp, "verify_replication_training_evidence_preflight", lambda sha, root: ev_id)
    
    class DummyCache:
        def __init__(self, *args): pass
    monkeypatch.setattr(cp, "DerivedCache", DummyCache)
    monkeypatch.setattr(cp, "build_frozen_populations", lambda cache: None)
    monkeypatch.setattr(cp, "build_job_specs", lambda pops, ev, path, sha: specs)
    
    # Phase 1: Worker crashes on 11th job
    crash_count_file = str(tmp_path / "crash_count.txt")
    with open(crash_count_file, "w") as f:
        f.write("0")
    monkeypatch.setenv("CHESSHEAT_TEST_REP_COUNT_FILE", crash_count_file)
    
    with pytest.raises(RuntimeError, match="SIMULATED_WORKER_CRASH_AFTER_10_JOBS"):
        run_training_parent(
            approved_sha=REPLICATION_EVIDENCE_COMMIT,
            cache_path="dummy",
            cache_sha=REPLICATION_CACHE_SHA,
            result_dir=result_dir,
            worker_fn=_mock_crashing_worker,
            lineage="V7_REPLICATION_1"
        )
        
    # Verify disk state after crash
    files = [f for f in os.listdir(result_dir) if f.endswith(".json")]
    assert len(files) == 10, f"Expected 10 files saved before crash, got {len(files)}"
    assert not any(f.startswith(".tmp") for f in os.listdir(result_dir)), "No partial tmp files should remain"
    
    # Phase 2: Restart in fresh context with completing worker
    completing_count_file = str(tmp_path / "completing_count.txt")
    with open(completing_count_file, "w") as f:
        f.write("0")
    monkeypatch.setenv("CHESSHEAT_TEST_REP_COMPLETING_COUNT_FILE", completing_count_file)
    
    verdict = run_training_parent(
        approved_sha=REPLICATION_EVIDENCE_COMMIT,
        cache_path="dummy",
        cache_sha=REPLICATION_CACHE_SHA,
        result_dir=result_dir,
        worker_fn=_mock_completing_worker,
        lineage="V7_REPLICATION_1"
    )
    
    assert verdict == "STOP_BEFORE_SCIENTIFIC_ANALYSIS"
    with open(completing_count_file, "r") as f:
        completed_count = int(f.read().strip())
    assert completed_count == 150, f"Expected 150 missing jobs executed, got {completed_count}"
    
    all_files = [f for f in os.listdir(result_dir) if f.endswith(".json")]
    assert len(all_files) == 160
    
    # Phase 3: Second restart on fully completed directory -> executes 0 jobs
    with open(completing_count_file, "w") as f:
        f.write("0")
        
    verdict_subsequent = run_training_parent(
        approved_sha=REPLICATION_EVIDENCE_COMMIT,
        cache_path="dummy",
        cache_sha=REPLICATION_CACHE_SHA,
        result_dir=result_dir,
        worker_fn=_mock_completing_worker,
        lineage="V7_REPLICATION_1"
    )
    assert verdict_subsequent == "STOP_BEFORE_SCIENTIFIC_ANALYSIS"
    with open(completing_count_file, "r") as f:
        zero_count = int(f.read().strip())
    assert zero_count == 0, "Subsequent rerun must execute 0 jobs"
    
    # Phase 4: Tampering with a replication envelope on disk fails closed
    corrupt_file = os.path.join(result_dir, all_files[0])
    with open(corrupt_file, "r") as f:
        data = json.load(f)
    data["payload"]["best_epoch"] = 999
    p_str = json.dumps(data["payload"], sort_keys=True, separators=(',', ':'))
    data["payload_sha256"] = hashlib.sha256(p_str.encode()).hexdigest()
    with open(corrupt_file, "w") as f:
        json.dump(data, f)
        
    with pytest.raises(ValueError, match="best_epoch bounds error"):
        run_training_parent(
            approved_sha=REPLICATION_EVIDENCE_COMMIT,
            cache_path="dummy",
            cache_sha=REPLICATION_CACHE_SHA,
            result_dir=result_dir,
            worker_fn=_mock_completing_worker,
            lineage="V7_REPLICATION_1"
        )


# --- Test 8: CLI Runner Lineage Wiring ---

def test_cli_runner_lineage_dispatch(monkeypatch):
    """Verify scripts/run_cp_representation_efficiency.py correctly configures cache and result_dir per lineage."""
    import sys
    repo_root = os.path.abspath(".")
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    import scripts.run_cp_representation_efficiency as cli
    
    recorded_calls = []
    def fake_run_training_parent(approved_sha, cache_path, cache_sha, result_dir, lineage):
        recorded_calls.append({
            "approved_sha": approved_sha,
            "cache_path": cache_path,
            "cache_sha": cache_sha,
            "result_dir": result_dir,
            "lineage": lineage
        })
        
    monkeypatch.setattr(cli, "run_training_parent", fake_run_training_parent)
    monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", REPLICATION_EVIDENCE_COMMIT)
    
    # 1. Run with --lineage V7_REPLICATION_1
    monkeypatch.setattr("sys.argv", ["run.py", "--mode", "train", "--lineage", "V7_REPLICATION_1"])
    cli.main()
    assert len(recorded_calls) == 1
    call = recorded_calls[0]
    assert call["lineage"] == "V7_REPLICATION_1"
    assert call["cache_path"] == "artifacts/research/cp_target_labels_2026_07/cp_target_pair_labels_v7_rep1.jsonl"
    assert call["cache_sha"] == REPLICATION_CACHE_SHA
    assert call["result_dir"] == "artifacts/research/cp_representation_efficiency_training_v7_rep1/worker_results"
    
    # 2. Run with default lineage (V6_HISTORICAL)
    recorded_calls.clear()
    monkeypatch.setattr("sys.argv", ["run.py", "--mode", "train"])
    cli.main()
    assert len(recorded_calls) == 1
    call_v6 = recorded_calls[0]
    assert call_v6["lineage"] == "V6_HISTORICAL"
    assert call_v6["cache_path"] == "artifacts/research/cp_target_labels_2026_07/cp_target_pair_labels_v6.jsonl"
    assert call_v6["cache_sha"] == V6_LABEL_SCIENTIFIC_SHA
    assert call_v6["result_dir"] == "artifacts/research/cp_representation_efficiency_training_v1/worker_results"
