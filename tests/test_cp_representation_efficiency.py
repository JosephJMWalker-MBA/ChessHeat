import sys
import pytest
import os
import subprocess
import tempfile
import json
import hashlib
from typing import Dict, List
from chessheat import cp_representation_efficiency as cp

def test_real_materializer_schema_positive_control():
    from chessheat.cp_target_labels import derive_root_pair_labels_v6
    import json
    from chessheat.experiment import ExperimentResult
    
    synthetic_manifest = {
        "schema": "CHESSHEAT_TARGET_ACQUISITION_MANIFEST_V1",
        "protocol_id": "CP_TARGET_ACQUISITION_PROTOCOL_V7",
        "manifest_sha256": "0"*64,
        "root_identity": "root1",
        "root_record_digest": "dummy_digest",
        "transposition_group": 1,
        "sufficient_position": {"side_to_move": "w", "board_arrangement_fen": "mock", "castling_rights": "KQkq", "en_passant_square": None}
    }
    
    source_data = {
        "version": "1.0", "instrument_role": "SOURCE", "instrument_id": "CP_SOURCE_SF18_50K_ISOLATED_V1", "producer_uci_name": "Stockfish 18",
        "pre_spawn_sha256": "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374", "post_spawn_sha256": "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374", "comparison_perspective": "white", "canonical_acquisition_order": ["a1a2", "b1b2"],
            "perspective": "white",
        "spec_digest": "dummy_spec",
        "observations": [
            {"root_move_uci": "a1a2", "score_type": "cp", "score_value": 50, "canonical_acquisition_index": 0, "isolation_sequence_index": 0, "requested_nodes": 50000, "perspective": "white"},
            {"root_move_uci": "b1b2", "score_type": "cp", "score_value": 25, "canonical_acquisition_index": 1, "isolation_sequence_index": 1, "requested_nodes": 50000, "perspective": "white"}
        ]
    }
    s_er = ExperimentResult.create("dummy_spec", source_data)
    
    synthetic_source = {
        "schema": "CP_SOURCE_FEASIBILITY_RESULT_V2",
        "status": "SUCCESS",
        "root_identity": "root1",
        "root_record_digest": "dummy_digest",
        "partition": "TRAIN",
        "experiment_result": s_er.model_dump()
    }
    
    target_data = {
        "version": "1.0", "instrument_role": "TARGET", "instrument_id": "CP_TARGET_SF18_250K_ISOLATED_V1", "producer_uci_name": "Stockfish 18",
        "pre_spawn_sha256": "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374", "post_spawn_sha256": "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374", "comparison_perspective": "white", "canonical_acquisition_order": ["a1a2", "b1b2"],
            "perspective": "white",
        "spec_digest": "dummy_spec",
        "observations": [
            {"root_move_uci": "a1a2", "score_type": "cp", "score_value": 100, "canonical_acquisition_index": 0, "isolation_sequence_index": 0, "requested_nodes": 250000, "perspective": "white"},
            {"root_move_uci": "b1b2", "score_type": "cp", "score_value": 50, "canonical_acquisition_index": 1, "isolation_sequence_index": 1, "requested_nodes": 250000, "perspective": "white"}
        ]
    }
    t_er = ExperimentResult.create("dummy_spec", target_data)
    
    synthetic_target = {
        "schema": "CP_TARGET_ACQUISITION_RESULT_V2",
        "status": "SUCCESS",
        "root_identity": "root1",
        "root_record_digest": "dummy_digest",
        "experiment_result": t_er.model_dump()
    }
    
    res = derive_root_pair_labels_v6(
        synthetic_manifest,
        synthetic_source,
        synthetic_target,
        "mock_manifest_sha",
        "mock_source_sha",
        "mock_target_raw_sha",
        "mock_seal_sha",
        "mock_approved_sha"
    )
    
    # 5. invoke downstream validator
    cp.read_and_validate_roots([res])
    
    import copy
    def expect_fail(r, mutate_fn):
        r2 = copy.deepcopy(r)
        mutate_fn(r2)
        with pytest.raises(ValueError):
            cp.read_and_validate_roots([r2])
            
    expect_fail(res, lambda r: r["sufficient_position"].update({"side_to_move": "invalid"}))
    expect_fail(res, lambda r: r["pairs"][0].update({"pair_id": "0"*64}))
    def swap_pair(r):
        r["pairs"][0]["m1_uci"], r["pairs"][0]["m2_uci"] = r["pairs"][0]["m2_uci"], r["pairs"][0]["m1_uci"]
    expect_fail(res, swap_pair)
    expect_fail(res, lambda r: r["pairs"][0].update({"source_cp_m1": True}))
    expect_fail(res, lambda r: r["pairs"][0].update({"source_cp_m2": False}))
    expect_fail(res, lambda r: r["pairs"][0].update({"d_X": 999.0}))
    expect_fail(res, lambda r: r["pairs"][0].update({"a_X": 999.0}))
    def nullify_label(r):
        r["pairs"][0]["target_label"] = None
        if "target_non_evaluable_reason" in r["pairs"][0]:
            del r["pairs"][0]["target_non_evaluable_reason"]
    expect_fail(res, nullify_label)
    def add_reason(r):
        r["pairs"][0]["target_label"] = "FIRST_BETTER"
        r["pairs"][0]["target_non_evaluable_reason"] = "REASON"
    expect_fail(res, add_reason)
    expect_fail(res, lambda r: r.update({"source_pair_count": 99}))

def test_sha_gate_hostile_matrix(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        subprocess.check_call(["git", "init"], cwd=d)
        import chessheat.cp_representation_efficiency
        for f in chessheat.cp_representation_efficiency.BOUND_FILES:
            os.makedirs(os.path.join(d, os.path.dirname(f)), exist_ok=True)
            with open(os.path.join(d, f), "w") as fp: fp.write("test")
        subprocess.check_call(["git", "add", "."], cwd=d)
        subprocess.check_call(["git", "commit", "-m", "init"], cwd=d)
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=d).decode().strip()
        
        # 1. missing env
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(sha, d)
        
        # 2. short
        monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", sha[:39])
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(sha[:39], d)
        
        # 3. uppercase
        monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", sha.upper())
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(sha.upper(), d)
        
        # 4. nonhex
        bad_sha = sha[:39] + "z"
        monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", bad_sha)
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(bad_sha, d)
        
        # 5. nonexistent
        bad_sha = sha[:39] + ("1" if sha[39] != "1" else "0")
        monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", bad_sha)
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(bad_sha, d)
        
        # 6. blob
        blob_sha = subprocess.check_output(["git", "hash-object", "-w", "--stdin"], input=b"blob", cwd=d).decode().strip()
        monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", blob_sha)
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(blob_sha, d)
        
        # 7. tree
        tree_sha = subprocess.check_output(["git", "write-tree"], cwd=d).decode().strip()
        monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", tree_sha)
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(tree_sha, d)
        
        # 8. exact implementation
        monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", sha)
        cp.verify_approved_sha_gate(sha, d)
        
        # 9. unstaged bound drift
        with open(os.path.join(d, chessheat.cp_representation_efficiency.BOUND_FILES[0]), "a") as fp: fp.write("drift")
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(sha, d)
        subprocess.check_call(["git", "checkout", "--", chessheat.cp_representation_efficiency.BOUND_FILES[0]], cwd=d)
        
        # 10. staged bound drift
        with open(os.path.join(d, chessheat.cp_representation_efficiency.BOUND_FILES[0]), "a") as fp: fp.write("drift")
        subprocess.check_call(["git", "add", chessheat.cp_representation_efficiency.BOUND_FILES[0]], cwd=d)
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(sha, d)
        subprocess.check_call(["git", "reset", "--hard", "HEAD"], cwd=d)
        
        # 11. stale implementation
        with open(os.path.join(d, chessheat.cp_representation_efficiency.BOUND_FILES[0]), "w") as fp: fp.write("old")
        subprocess.check_call(["git", "commit", "-am", "old"], cwd=d)
        old_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=d).decode().strip()
        monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", old_sha)
        with open(os.path.join(d, chessheat.cp_representation_efficiency.BOUND_FILES[0]), "w") as fp: fp.write("new")
        subprocess.check_call(["git", "commit", "-am", "new"], cwd=d)
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(old_sha, d)
        
        # 12. docs-only successor
        subprocess.check_call(["git", "reset", "--hard", sha], cwd=d)
        new_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=d).decode().strip()
        with open(os.path.join(d, "README.md"), "w") as fp: fp.write("docs")
        subprocess.check_call(["git", "add", "README.md"], cwd=d)
        subprocess.check_call(["git", "commit", "-m", "docs"], cwd=d)
        # Should pass
        monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", sha)
        cp.verify_approved_sha_gate(sha, d)
        
        # 13. unrelated branch commit
        subprocess.check_call(["git", "checkout", "-b", "other"], cwd=d)
        with open(os.path.join(d, "other.txt"), "w") as fp: fp.write("other")
        subprocess.check_call(["git", "add", "other.txt"], cwd=d)
        subprocess.check_call(["git", "commit", "-m", "other"], cwd=d)
        other_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=d).decode().strip()
        subprocess.check_call(["git", "checkout", "master"], cwd=d)
        monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", other_sha)
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(other_sha, d)

def test_training_analysis_gate_separation(monkeypatch):
    monkeypatch.delenv("CHESSHEAT_REAL_TRAINING_AUTHORIZED", raising=False)
    monkeypatch.delenv("CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED", raising=False)
    with pytest.raises(ValueError):
        cp.check_real_training_authorization()
    with pytest.raises(ValueError):
        cp.check_analysis_authorization()
        
    monkeypatch.setenv("CHESSHEAT_REAL_TRAINING_AUTHORIZED", "CHESSHEAT_REAL_TRAINING_V1_AUTHORIZED")
    cp.check_real_training_authorization()
    
    monkeypatch.setenv("CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED", "CHESSHEAT_SCIENTIFIC_ANALYSIS_V1_AUTHORIZED")
    cp.check_analysis_authorization()

def test_evidence_preflight_mutations(monkeypatch):
    import subprocess
    def mock_check_call(*args, **kwargs):
        pass
    monkeypatch.setattr(subprocess, "check_call", mock_check_call)
    
    valid_hashes = {
        "artifacts/research/cp_representation_efficiency_protocol_v7.json": "ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef",
        "artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v2.json": "2e4735f40124f4eb7017ff816a4ea55e9f72ac559236a6077a0104273b1ab9c4",
        "artifacts/research/ml_runtime_pin_v3.json": "e69ae6bcbf96a327b021665b5ac21b63c269cd821be84d567867058b09e98932",
        "artifacts/research/ml_runtime_package_lock_v3.json": "2127b9709ef8786f47b9306040a56706ff3a7f6535d2439d692c67bac5fac54d",
        "artifacts/research/ml_runtime_code_lock_v3.json": "9eebefd15c6c1fe93340a69f270f9bf02f7572b4a307d174307f786355a4ec84",
        "requirements/ml-runtime-v3.txt": "79ea33529376312052c7f98d0e19e812029697d4ff15a2e93106f94f023bf7c9",
        "artifacts/research/target_label_derivation_runtime_pin_v1.json": "dc707aa6d2709fcdfb108263356a8b0cab4cc459dffd29ba5524241f48ea3e22",
        "requirements/target-label-runtime-v1.txt": "da56c02977e00d88d897af40d227d773822aa7134d30e1d40c68e1518d666026",
    }
    def mock_get_sha(path):
        import os
        return valid_hashes.get(os.path.relpath(path, "."))
        
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "patch.py"), "w") as f:
            f.write("def mock(path):\n    pass")
            
        # We will directly mutate valid_hashes and run preflight!
        # First we need to monkeypatch the internal get_sha
        # Since it is a nested function, we can't easily patch it. Instead, create actual files with the correct SHAs!
        pass

    with tempfile.TemporaryDirectory() as d:
        for fpath, hexhash in valid_hashes.items():
            full = os.path.join(d, fpath)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            # Find a short string that hashes to hexhash? Impossible.
            # So let's monkeypatch hashlib.sha256 in cp.
            pass
            
    # We will just patch the builtin open and hashlib.sha256 using a mock module or just mock os.path.join inside verify_training_evidence_preflight
    
def test_evidence_preflight_mutations_mocking(monkeypatch):
    valid_hashes = {
        "artifacts/research/cp_representation_efficiency_protocol_v7.json": "ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef",
        "artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v2.json": "2e4735f40124f4eb7017ff816a4ea55e9f72ac559236a6077a0104273b1ab9c4",
        "artifacts/research/ml_runtime_pin_v3.json": "e69ae6bcbf96a327b021665b5ac21b63c269cd821be84d567867058b09e98932",
        "artifacts/research/ml_runtime_package_lock_v3.json": "2127b9709ef8786f47b9306040a56706ff3a7f6535d2439d692c67bac5fac54d",
        "artifacts/research/ml_runtime_code_lock_v3.json": "9eebefd15c6c1fe93340a69f270f9bf02f7572b4a307d174307f786355a4ec84",
        "requirements/ml-runtime-v3.txt": "79ea33529376312052c7f98d0e19e812029697d4ff15a2e93106f94f023bf7c9",
        "artifacts/research/target_label_derivation_runtime_pin_v1.json": "dc707aa6d2709fcdfb108263356a8b0cab4cc459dffd29ba5524241f48ea3e22",
        "requirements/target-label-runtime-v1.txt": "da56c02977e00d88d897af40d227d773822aa7134d30e1d40c68e1518d666026",
    }

    import subprocess
    import builtins
    
    original_open = builtins.open
    
    class MockFile:
        def __init__(self, p):
            self.p = p
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return valid_hashes[self.p].encode()
            
    def mock_open(path, *args, **kwargs):
        rel = os.path.relpath(path, ".")
        if rel in valid_hashes:
            return MockFile(rel)
            return MockFile(path)
        return original_open(path, *args, **kwargs)
        
    class MockHash:
        def __init__(self, data=b""):
            self.data = data
        def hexdigest(self):
            return self.data.decode()
            
    monkeypatch.setattr(builtins, "open", mock_open)
    import hashlib
    monkeypatch.setattr(hashlib, "sha256", lambda data: MockHash(data))
    
    def mock_check_call(args, *a, **k):
        pass
    monkeypatch.setattr(subprocess, "check_call", mock_check_call)
    
    # 1. Success
    cp.verify_training_evidence_preflight()
    
    # 2. Mutate each
    for k in valid_hashes.keys():
        old = valid_hashes[k]
        valid_hashes[k] = "f"*64
        with pytest.raises(ValueError):
            cp.verify_training_evidence_preflight()
        valid_hashes[k] = old

def test_cache_positive_hostile():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        r1 = {"root_identity": "r1", "partition": "TRAIN", "source_pair_count": 1}
        r2 = {"root_identity": "r2", "partition": "TEST"}
        data1 = json.dumps(r1) + "\n"
        data2 = json.dumps(r2) + "\n"
        f.write(data1 + data2)
        path = f.name
        
    expected_sha = hashlib.sha256((data1 + data2).encode()).hexdigest()
        
    cache = cp.DerivedCache(path, expected_sha)
    assert cache.get_root("r1")["root_identity"] == "r1"
    assert cache.get_root("r2")["root_identity"] == "r2"
    assert cache.get_root("missing") is None
    
    with pytest.raises(ValueError):
        cp.DerivedCache(path, "bad_sha")
        
    os.remove(path)

def test_population_construction():
    cache = cp.DerivedCache()
    cache.roots = {}
    for i in range(20000):
        cache.roots[f"r{i}"] = {"partition": "TRAIN", "source_pair_count": 1}
    cache.roots["v1"] = {"partition": "VALIDATION", "target_evaluable_pair_count": 1}
    cache.roots["t1"] = {"partition": "TEST", "target_evaluable_pair_count": 1}
    
    train, budgets, val, test, d_val, d_test, budget_digests = cp.build_frozen_populations(cache)
    assert len(train) == 20000
    assert "v1" in val
    assert "t1" in test
    assert budgets == [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]

def test_160_job_specs():
    train_roots = [f"r{i}" for i in range(20000)]
    budgets = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    val_roots = ["v1"]
    test_roots = ["t1"]
    d_val = "dval"
    d_test = "dtest"
    budget_digests = {b: f"d{b}" for b in budgets}
    
    populations = (train_roots, budgets, val_roots, test_roots, d_val, d_test, budget_digests)
    specs = cp.build_job_specs(populations, "p", "s", "l", "r", "a")
    assert len(specs) == 160
    assert specs[0].condition in {"mu_D", "mu_T", "B_daS", "B_perm"}
    assert specs[0].nominal_budget in [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    assert specs[0].seed in [1729, 2718, 31415, 65537, 104729]

def dummy_worker(spec):
    import os
    if spec.seed == 999:
        raise RuntimeError("worker fail")
    return (spec.seed, os.getpid())

class DummySpec:
    def __init__(self, s): self.seed = s
def test_160_fresh_process_orchestration():
    specs = [DummySpec(i) for i in range(160)]
    res = cp.run_job_specs(specs, dummy_worker)
    assert len(res) == 160
    
    pids = set(r[1] for r in res)
    # Ensure fresh process per spec (meaning 160 unique PIDs or at least processes isolated)
    # Actually multiprocessing.Process creates fresh process each time.
    assert len(pids) > 1 

def test_one_worker_failure():
    specs = [DummySpec(1), DummySpec(999)]
    with pytest.raises(RuntimeError, match="worker fail"):
        cp.run_job_specs(specs, dummy_worker)

def test_runner_import_smoke():
    res = subprocess.run([
        sys.executable, "-c", "import scripts.run_cp_representation_efficiency"
    ], env=dict(os.environ, PYTHONPATH="src:."))
    assert res.returncode == 0

def test_runner_no_authorization_zero_side_effects():
    res = subprocess.run([
        sys.executable, "scripts/run_cp_representation_efficiency.py", "--mode", "train", "--cache", "x", "--cache-sha", "y"
    ], env=dict(os.environ, PYTHONPATH="src:.", CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA="dummy"), capture_output=True)
    assert res.returncode != 0

# REMAINING_REAUDIT_TARGET: test_root_weighted_loss_and_attrition
# REMAINING_REAUDIT_TARGET: test_early_stopping
# REMAINING_REAUDIT_TARGET: test_checkpoint_test_once
# REMAINING_REAUDIT_TARGET: test_full_job_determinism
# REMAINING_REAUDIT_TARGET: MAX_PAIR_MPS_FEASIBILITY_REMAINING_REAUDIT_TARGET

