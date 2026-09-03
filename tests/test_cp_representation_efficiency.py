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
    import json, copy
    from chessheat.experiment import ExperimentResult
    import chessheat.cp_representation_efficiency as cp

    synthetic_manifest = {
        "schema": "CHESSHEAT_TARGET_ACQUISITION_MANIFEST_V1",
        "protocol_id": "CP_TARGET_ACQUISITION_PROTOCOL_V7",
        "manifest_sha256": "0"*64,
        "root_identity": "root1",
        "root_record_digest": "dummy_digest",
        "transposition_group": 1,
        "sufficient_position": {"side_to_move": "w", "board_arrangement_fen": "mock", "castling_rights": "KQkq", "en_passant_square": None}
    }

    # AT LEAST THREE SOURCE CP moves
    # We want strictly increasing m: e.g. "a1a2", "b1b2", "c1c2"
    # But we want their SHA256 of "CHESSHEAT_TARGET_PAIR_V1|root1|m1|m2" to be NON-MONOTONIC.
    # We will pick 4 moves so we can form pairs.
    # Let's use a1a2, a1a3, a1a4, a1a5 as source moves.
    source_data = {
        "version": "1.0", "instrument_role": "SOURCE", "instrument_id": "CP_SOURCE_SF18_50K_ISOLATED_V1", "producer_uci_name": "Stockfish 18",
        "pre_spawn_sha256": "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374", "post_spawn_sha256": "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374", "comparison_perspective": "white", 
        "canonical_acquisition_order": ["a1a2", "b1b2", "c1c2", "d1d2"],
        "perspective": "white",
        "spec_digest": "dummy_spec",
        "observations": [
            {"root_move_uci": "a1a2", "score_type": "cp", "score_value": 50, "canonical_acquisition_index": 0, "isolation_sequence_index": 0, "requested_nodes": 50000, "perspective": "white"},
            {"root_move_uci": "b1b2", "score_type": "cp", "score_value": 25, "canonical_acquisition_index": 1, "isolation_sequence_index": 1, "requested_nodes": 50000, "perspective": "white"},
            {"root_move_uci": "c1c2", "score_type": "cp", "score_value": 10, "canonical_acquisition_index": 2, "isolation_sequence_index": 2, "requested_nodes": 50000, "perspective": "white"},
            {"root_move_uci": "d1d2", "score_type": "cp", "score_value": 5, "canonical_acquisition_index": 3, "isolation_sequence_index": 3, "requested_nodes": 50000, "perspective": "white"}
        ]
    }
    s_er = ExperimentResult.create("dummy_spec", source_data)
    synthetic_source = {
        "schema": "CP_SOURCE_FEASIBILITY_RESULT_V2", "status": "SUCCESS", "root_identity": "root1",
        "root_record_digest": "dummy_digest", "partition": "TRAIN", "experiment_result": s_er.model_dump()
    }

    target_data = {
        "version": "1.0", "instrument_role": "TARGET", "instrument_id": "CP_TARGET_SF18_250K_ISOLATED_V1", "producer_uci_name": "Stockfish 18",
        "pre_spawn_sha256": "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374", "post_spawn_sha256": "ae4c93fa9676ca7750d0714342fd8a5b1d018000fc6e0f6cedf112067b5ef374", "comparison_perspective": "white", 
        "canonical_acquisition_order": ["a1a2", "b1b2", "c1c2", "d1d2"],
        "perspective": "white",
        "spec_digest": "dummy_spec",
        "observations": [
            {"root_move_uci": "a1a2", "score_type": "cp", "score_value": 100, "canonical_acquisition_index": 0, "isolation_sequence_index": 0, "requested_nodes": 250000, "perspective": "white"},
            {"root_move_uci": "b1b2", "score_type": "cp", "score_value": 50, "canonical_acquisition_index": 1, "isolation_sequence_index": 1, "requested_nodes": 250000, "perspective": "white"},
            {"root_move_uci": "c1c2", "score_type": "cp", "score_value": 30, "canonical_acquisition_index": 2, "isolation_sequence_index": 2, "requested_nodes": 250000, "perspective": "white"},
            {"root_move_uci": "d1d2", "score_type": "cp", "score_value": 10, "canonical_acquisition_index": 3, "isolation_sequence_index": 3, "requested_nodes": 250000, "perspective": "white"}
        ]
    }
    t_er = ExperimentResult.create("dummy_spec", target_data)
    synthetic_target = {
        "schema": "CP_TARGET_ACQUISITION_RESULT_V2", "status": "SUCCESS", "root_identity": "root1",
        "root_record_digest": "dummy_digest", "experiment_result": t_er.model_dump()
    }

    res = derive_root_pair_labels_v6(
        synthetic_manifest, synthetic_source, synthetic_target,
        "mock_manifest_sha", "mock_source_sha", "mock_target_raw_sha", "mock_seal_sha", "mock_approved_sha"
    )

    assert len(res["pairs"]) >= 3
    # Check that m is strictly increasing
    for i in range(len(res["pairs"])-1):
        p1 = res["pairs"][i]
        p2 = res["pairs"][i+1]
        assert (p1["m1_uci"], p1["m2_uci"]) < (p2["m1_uci"], p2["m2_uci"])

    # Check non-monotonic SHA
    shas = [p["pair_id"] for p in res["pairs"]]
    PAIR_SHA_SEQUENCE_NONMONOTONIC = any(shas[i] > shas[i+1] for i in range(len(shas)-1))
    assert PAIR_SHA_SEQUENCE_NONMONOTONIC

    cp.read_and_validate_roots([res])

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
    
    # EXACT DOMAIN
    expect_fail(res, lambda r: r["pairs"][0].update({"source_cp_m1": True}))
    expect_fail(res, lambda r: r["pairs"][0].update({"source_cp_m2": False}))
    expect_fail(res, lambda r: r["pairs"][0].update({"source_cp_m1": 1.0}))
    expect_fail(res, lambda r: r["pairs"][0].update({"source_cp_m2": "25"}))
    expect_fail(res, lambda r: r["pairs"][0].update({"source_cp_m1": None}))

    # BAD HEADER VALUES
    expect_fail(res, lambda r: r.update({"schema": "BAD"}))
    expect_fail(res, lambda r: r.update({"label_derivation_protocol": "BAD"}))
    expect_fail(res, lambda r: r.update({"protocol_id": "BAD"}))
    expect_fail(res, lambda r: r.update({"partition": "BAD"}))

    expect_fail(res, lambda r: r["pairs"][0].update({"d_X": 999.0}))
    expect_fail(res, lambda r: r["pairs"][0].update({"a_X": 999.0}))
    
    def nullify_label(r):
        r["pairs"][0]["target_label"] = None
        r["pairs"][0]["target_non_evaluable_reason"] = "OTHER"
    def nullify_label2(r):
        r["pairs"][0]["target_label"] = None
        if "target_non_evaluable_reason" in r["pairs"][0]:
            del r["pairs"][0]["target_non_evaluable_reason"]

    expect_fail(res, nullify_label)
    expect_fail(res, nullify_label2)
    
    def add_reason(r):
        r["pairs"][0]["target_label"] = "FIRST_BETTER"
        r["pairs"][0]["target_non_evaluable_reason"] = "REASON"
    expect_fail(res, add_reason)

    # UNIQUE ROOT IDENTITIES
    with pytest.raises(ValueError):
        cp.read_and_validate_roots([res, res])

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
    cache.roots["CHESSHEAT_TARGET_ROOT_v1"] = {"partition": "VALIDATION", "target_evaluable_pair_count": 1}
    cache.roots["t1"] = {"partition": "TEST", "target_evaluable_pair_count": 1}
    
    train, budgets, val, test, d_val, d_test, budget_digests = cp.build_frozen_populations(cache)
    assert len(train) == 20000
    assert "CHESSHEAT_TARGET_ROOT_v1" in val
    assert "t1" in test
    assert budgets == [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]

def test_160_job_specs():
    import chessheat.cp_representation_efficiency as cp
    class MockEv:
        protocol_v7_sha = "a"
        seal_v2_sha = "b"
        label_scientific_sha = "c"
        runtime_v3_pin_sha = "d"
    
    train = ["r%d"%i for i in range(25000)]
    budgets = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    val = ["CHESSHEAT_TARGET_ROOT_v1"]
    test = ["t1"]
    bd = {b: str(b) for b in budgets}
    pops = (train, budgets, val, test, "val_d", "test_d", bd)
    
    specs = cp.build_job_specs(pops, MockEv(), "cache_path", "approved")
    
    expected_tuples = {(cond, b, s) for cond in ["mu_D", "mu_T", "B_daS", "B_perm"]
                       for b in budgets for s in [1729, 2718, 31415, 65537, 104729]}
    
    actual_tuples = {(s.condition, s.nominal_budget, s.seed) for s in specs}
    assert actual_tuples == expected_tuples
    assert len(actual_tuples) == 160
    assert len(specs) == 160

def dummy_worker(spec):
    return (spec.condition, spec.nominal_budget, spec.seed)
    
def test_160_fresh_process_orchestration():
    import chessheat.cp_representation_efficiency as cp
    class MockEv:
        protocol_v7_sha = "a"
        seal_v2_sha = "b"
        label_scientific_sha = "c"
        runtime_v3_pin_sha = "d"
    train = ["r%d"%i for i in range(25000)]
    budgets = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    pops = (train, budgets, [], [], "val_d", "test_d", {b: str(b) for b in budgets})
    specs = cp.build_job_specs(pops, MockEv(), "cache_path", "approved")
    
    results = cp.run_job_specs(specs, dummy_worker)
    
    expected_ids = {(s.condition, s.nominal_budget, s.seed) for s in specs}
    actual_ids = set(results)
    assert len(results) == 160
    assert len(specs) == 160
    assert actual_ids == expected_ids

    # The actual launch_count is tested by checking len(results) mapping 1-to-1 with len(specs)


def failing_worker_global(spec):
    if spec.nominal_budget == 1000:
        raise RuntimeError("worker fail")
    return (spec.condition, spec.nominal_budget, spec.seed)

def test_one_worker_failure():
    import chessheat.cp_representation_efficiency as cp
    class MockEv:
        protocol_v7_sha = "a"
        seal_v2_sha = "b"
        label_scientific_sha = "c"
        runtime_v3_pin_sha = "d"
    train = ["r%d"%i for i in range(25000)]
    budgets = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    pops = (train, budgets, [], [], "val_d", "test_d", {b: str(b) for b in budgets})
    specs = cp.build_job_specs(pops, MockEv(), "cache_path", "approved")
    
    with pytest.raises(RuntimeError, match="worker fail"):
        cp.run_job_specs(specs, failing_worker_global)

def test_runner_import_smoke():
    res = subprocess.run([
        sys.executable, "-c", "import scripts.run_cp_representation_efficiency"
    ], env=dict(os.environ, PYTHONPATH="src:."))
    assert res.returncode == 0

def test_runner_no_authorization_zero_side_effects(tmp_path, monkeypatch):
    import os, subprocess
    import chessheat.cp_representation_efficiency as cp
    
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.check_call(["git", "init"], cwd=str(repo))
    
    for fpath in cp.BOUND_FILES:
        full = repo / fpath
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("dummy")
        subprocess.check_call(["git", "add", str(full)], cwd=str(repo))
    
    subprocess.check_call(["git", "commit", "-m", "init"], cwd=str(repo))
    commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo)).decode().strip()
    
    os.environ["CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA"] = commit_sha
    if "CHESSHEAT_REAL_TRAINING_AUTHORIZED" in os.environ:
        del os.environ["CHESSHEAT_REAL_TRAINING_AUTHORIZED"]
        
    calls = {"preflight": 0, "cache": 0, "pops": 0, "jobs": 0}
    
    def spy_preflight(*args, **kwargs): calls["preflight"] += 1
    monkeypatch.setattr(cp, "verify_training_evidence_preflight", spy_preflight)
    class SpyCache:
        def __init__(self, *args, **kwargs): calls["cache"] += 1
    monkeypatch.setattr(cp, "DerivedCache", SpyCache)
    def spy_pops(*args, **kwargs): calls["pops"] += 1
    monkeypatch.setattr(cp, "build_frozen_populations", spy_pops)
    def spy_jobs(*args, **kwargs): calls["jobs"] += 1
    monkeypatch.setattr(cp, "run_job_specs", spy_jobs)
        
    import pytest
    with pytest.raises(ValueError, match='Real training not authorized'):
        cp.run_training_parent(commit_sha, "mock", "mock", repo_root=str(repo))
        
    assert calls["preflight"] == 0
    assert calls["cache"] == 0
    assert calls["pops"] == 0
    assert calls["jobs"] == 0
def test_evidence_preflight_mutations_mocking(monkeypatch, tmp_path):
    import os, subprocess
    import chessheat.cp_representation_efficiency as cp
    
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.check_call(["git", "init"], cwd=str(repo))
    f = repo / "test.txt"
    
    f.write_text("audit")
    subprocess.check_call(["git", "add", "test.txt"], cwd=str(repo))
    subprocess.check_call(["git", "commit", "-m", "audit"], cwd=str(repo))
    commit_audit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo)).decode().strip()
    
    f.write_text("supplement")
    subprocess.check_call(["git", "add", "test.txt"], cwd=str(repo))
    subprocess.check_call(["git", "commit", "-m", "supplement"], cwd=str(repo))
    commit_supp = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo)).decode().strip()
    
    f.write_text("approved")
    subprocess.check_call(["git", "add", "test.txt"], cwd=str(repo))
    subprocess.check_call(["git", "commit", "-m", "approved"], cwd=str(repo))
    commit_app = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo)).decode().strip()
    
    subprocess.check_call(["git", "checkout", "--orphan", "unrelated"], cwd=str(repo))
    f.write_text("unrelated")
    subprocess.check_call(["git", "add", "test.txt"], cwd=str(repo))
    subprocess.check_call(["git", "commit", "-m", "unrelated"], cwd=str(repo))
    commit_unrelated = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo)).decode().strip()
    # no checkout needed
    

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
    
    import builtins
    import os
    original_open = builtins.open
    class MockFile:
        def __init__(self, p): self.p = p
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return valid_hashes[self.p].encode()
    def mock_open(path, *args, **kwargs):
        rel = os.path.relpath(path, str(repo))
        if rel in valid_hashes:
            return MockFile(rel)
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", mock_open)
    
    class MockHash:
        def __init__(self, data=b""): self.data = data
        def hexdigest(self): return self.data.decode()
    import hashlib
    monkeypatch.setattr(hashlib, "sha256", lambda data: MockHash(data))

    
    original_check_call = subprocess.check_call
    def mock_check_call(args, cwd=None, stderr=None):
        if "merge-base" in args:
            arg_list = list(args)
            if arg_list[3] == "2f7560a38427754404c6f1ee6115db950d18815c": arg_list[3] = commit_audit
            if arg_list[3] == "87e1edad72d2899d0bc7a05d11d9601d60b7cba3": arg_list[3] = commit_supp
            return original_check_call(arg_list, cwd=cwd, stderr=stderr)
        return original_check_call(args, cwd=cwd, stderr=stderr)
    subprocess.check_call = mock_check_call
    
    try:
        res = cp.verify_training_evidence_preflight(commit_app, repo_root=str(repo))
        assert res.label_scientific_sha == "c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2"
        
        import pytest
        with pytest.raises(ValueError, match="evidence audit commit missing or not ancestor"):
            cp.verify_training_evidence_preflight(commit_unrelated, repo_root=str(repo))
    finally:
        subprocess.check_call = original_check_call
        

def test_static_function_counts():
    import ast
    import chessheat.cp_representation_efficiency as cp
    import inspect
    
    source = inspect.getsource(cp)
    tree = ast.parse(source)
    
    rtj_count = sum(1 for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_training_job")
    assert rtj_count == 1, "Expected exactly 1 run_training_job"
    
    crpd_count = sum(1 for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "canonical_root_population_digest")
    assert crpd_count == 1, "Expected exactly 1 canonical_root_population_digest"
    
    assert "Dummy mock for actual learner" not in source

def test_run_training_job_symbol_binding():
    import chessheat.cp_representation_efficiency as cp
    import inspect
    source = inspect.getsource(cp.run_training_job)
    
    assert "configure_runtime" in source
    assert "initialize_model_cpu_then_mps" in source
    assert "build_frozen_adam" in source
    assert "get_epoch_order" in source
    assert "evaluate_roots" in source
    
    assert "Dummy mock" not in source
    assert "best_epoch = 1" not in source
    assert "0.5" not in source
    assert '"a"*64' not in source

def test_validation_test_order_regression():
    import chessheat.cp_representation_efficiency as cp
    
    # We create a fake cache that returns roots in some weird order.
    class DummyCacheOrder:
        def __init__(self):
            self.roots = {
                "t1": {"partition": "TRAIN", "source_pair_count": 1},
                "t2": {"partition": "TRAIN", "source_pair_count": 1},
                "v_z": {"partition": "VALIDATION", "target_evaluable_pair_count": 1},
                "v_a": {"partition": "VALIDATION", "target_evaluable_pair_count": 1},
                "v_m": {"partition": "VALIDATION", "target_evaluable_pair_count": 1},
                "t_z": {"partition": "TEST", "target_evaluable_pair_count": 1},
                "t_a": {"partition": "TEST", "target_evaluable_pair_count": 1},
                "t_m": {"partition": "TEST", "target_evaluable_pair_count": 1},
            }
            # mock 20000 limit
            for i in range(20000):
                self.roots[f"x{i}"] = {"partition": "TRAIN", "source_pair_count": 1}
                
        def get_root(self, rid, *args):
            return {"schema": "CP_TARGET_PAIR_LABEL_ROOT_V6", "root_identity": rid, "sufficient_position": {"side_to_move": "w"}, "target_label": None, "target_non_evaluable_reason": "TARGET_ACQUISITION_FAILURE"}

    dummy_cache = DummyCacheOrder()
    
    train_ret, budgets, v_ret, t_ret, v_dig, t_dig, b_digs = cp.build_frozen_populations(dummy_cache)
    
    v_ids = v_ret
    t_ids = t_ret
    
    assert v_ids == ("v_a", "v_m", "v_z")
    assert t_ids == ("t_a", "t_m", "t_z")
    
    # Check digests
    v_digest = cp.canonical_root_population_digest(v_ids)
    t_digest = cp.canonical_root_population_digest(t_ids)
    
    # Also we should check if they equal the digest of the returned tuple directly
    assert v_digest == cp.canonical_root_population_digest(v_ret)

def test_index_only_drift_failure(monkeypatch, tmp_path):
    import os, subprocess
    import chessheat.cp_representation_efficiency as cp
    
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.check_call(["git", "init"], cwd=str(repo))
    
    f = repo / "test.txt"
    f.write_text("audit")
    subprocess.check_call(["git", "add", "test.txt"], cwd=str(repo))
    subprocess.check_call(["git", "commit", "-m", "audit"], cwd=str(repo))
    commit_audit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo)).decode().strip()
    
    f.write_text("approved")
    subprocess.check_call(["git", "add", "test.txt"], cwd=str(repo))
    subprocess.check_call(["git", "commit", "-m", "approved"], cwd=str(repo))
    commit_app = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo)).decode().strip()
    
    # modify bound file
    f.write_text("modified")
    # git add
    subprocess.check_call(["git", "add", "test.txt"], cwd=str(repo))
    
    # In index-only drift, working tree matches index, so git diff --quiet is clean
    subprocess.check_call(["git", "diff", "--quiet"], cwd=str(repo))
    
    # git diff --cached --quiet => dirty
    import pytest
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_call(["git", "diff", "--cached", "--quiet"], cwd=str(repo))
    
    # verify_approved_sha_gate => FAIL
    # We must patch get_sha or rely on the same builtins.open patch
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
    
    import builtins
    original_open = builtins.open
    class MockFile:
        def __init__(self, p): self.p = p
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return valid_hashes[self.p].encode()
    def mock_open(path, *args, **kwargs):
        rel = os.path.relpath(path, str(repo))
        if rel in valid_hashes:
            return MockFile(rel)
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", mock_open)
    
    class MockHash:
        def __init__(self, data=b""): self.data = data
        def hexdigest(self): return self.data.decode()
    import hashlib
    monkeypatch.setattr(hashlib, "sha256", lambda data: MockHash(data))

    monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", commit_app)

    with pytest.raises(ValueError, match="Dirty working tree"):
        cp.verify_approved_sha_gate(commit_app, repo_root=str(repo))

def test_worker_binding():
    import chessheat.cp_representation_efficiency as cp
    
    spec = cp.JobSpec(
        condition="C", nominal_budget=1, seed=1,
        nominal_root_ids=["r1"], nominal_root_population_digest=cp.canonical_root_population_digest(["r1"]),
        validation_root_ids=["CHESSHEAT_TARGET_ROOT_v1"], validation_population_digest=cp.canonical_root_population_digest(["CHESSHEAT_TARGET_ROOT_v1"]),
        test_root_ids=["t1"], test_population_digest=cp.canonical_root_population_digest(["t1"]),
        protocol_v7_sha="b", seal_v2_sha="c", label_scientific_sha="d",
        runtime_v3_identity="e", runtime_v3_pin_sha="f",
        approved_implementation_sha="a", cache_path=""
    )
    
    original_rtj = cp.run_training_job
    call_count = 0
    valid_res = {
        "schema": "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V14",
        "condition": "C",
        "nominal_budget": 1,
        "seed": 1,
        "nominal_root_population_digest": cp.canonical_root_population_digest(["r1"]),
        "validation_population_digest": cp.canonical_root_population_digest(["CHESSHEAT_TARGET_ROOT_v1"]),
        "test_population_digest": cp.canonical_root_population_digest(["t1"]),
        "nominal_root_count": 1,
        "effective_training_root_count": 1,
        "effective_root_population_digest": "",
        "best_epoch": 0,
        "best_validation_root_nll": 0,
        "epochs_completed": 0,
        "validation_trace": [],
        "test_evaluation_count": 1,
        "test_root_ids": ("t1",),
        "test_root_losses": {},
        "canonical_model_state_sha": ""
    }
    
    def mock_rtj(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return valid_res.copy()
        
    cp.run_training_job = mock_rtj
    
    # We must patch DerivedCache and read_and_validate_roots to avoid file reads
    class MockCache:
        def __init__(self, *args): pass
        def get_root(self, rid, *args):
            return {"schema": "CP_TARGET_PAIR_LABEL_ROOT_V6", "root_identity": rid, "sufficient_position": {"side_to_move": "w"}, "target_label": None, "target_non_evaluable_reason": "TARGET_ACQUISITION_FAILURE"}
    
    original_cache = cp.DerivedCache
    cp.DerivedCache = MockCache
    original_rv = cp.read_and_validate_roots
    cp.read_and_validate_roots = lambda x: x
    
    try:
        # positive
        res = cp.run_downstream_worker(spec)
        assert call_count == 1
        assert res["schema"] == "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V14"
        assert res["approved_implementation_sha"] == "a"
        
        # hostile mutations
        import pytest
        mutations = [
            ("schema", "WRONG"), ("schema", "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V13"), ("schema", "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V13"), ("schema", "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V13"),
            ("condition", "WRONG"),
            ("nominal_budget", 99),
            ("seed", 99),
            ("nominal_root_count", 99),
            ("nominal_root_population_digest", "WRONG"),
            ("validation_population_digest", "WRONG"),
            ("test_population_digest", "WRONG"),
            ("effective_training_root_count", 2), # > nominal
            ("test_evaluation_count", 0),
            ("test_root_ids", ("WRONG",))
        ]
        
        for k, v in mutations:
            def make_bad(k, v):
                def bad_mock(*args, **kwargs):
                    r = valid_res.copy()
                    r[k] = v
                    return r
                return bad_mock
            cp.run_training_job = make_bad(k, v)
            with pytest.raises(ValueError):
                cp.run_downstream_worker(spec)
                
    finally:
        cp.run_training_job = original_rtj
        cp.DerivedCache = original_cache
        cp.read_and_validate_roots = original_rv

def test_parent_completeness_with_fake_worker():
    import chessheat.cp_representation_efficiency as cp
    import pytest
    
    # create dummy job_specs
    specs = [
        cp.JobSpec("C", 1, 1, ["r"], "nd", ["v"], "vd", ["t"], "td", "b", "c", "d", "e", "f", "a", "")
    ]
    
    valid_res = {
        "schema": "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V14",
        "condition": "C", "nominal_budget": 1, "seed": 1,
        "approved_implementation_sha": "a", "protocol_v7_sha": "b", "seal_v2_sha": "c",
        "label_scientific_sha": "d", "runtime_v3_identity": "e", "runtime_v3_pin_sha": "f",
        "nominal_root_population_digest": "nd", "validation_population_digest": "vd", "test_population_digest": "td",
        "test_root_ids": ("t",)
    }
    
    # 1. positive check
    cp.validate_completed_worker_results(specs, [valid_res.copy()])
    
    # 2. negative checks
    with pytest.raises(ValueError, match="Expected"):
        cp.validate_completed_worker_results(specs, [])  # missing
    with pytest.raises(ValueError, match="Expected"):
        cp.validate_completed_worker_results(specs, [valid_res.copy(), valid_res.copy()])  # duplicate length
        
    specs_2 = [
        cp.JobSpec("C", 1, 1, ["r"], "nd", ["v"], "vd", ["t"], "td", "b", "c", "d", "e", "f", "a", ""),
        cp.JobSpec("C2", 1, 1, ["r"], "nd", ["v"], "vd", ["t"], "td", "b", "c", "d", "e", "f", "a", "")
    ]
    with pytest.raises(ValueError, match="incompleteness or duplicates"):
        cp.validate_completed_worker_results(specs_2, [valid_res.copy(), valid_res.copy()])  # duplicate items
        
    mutations = [
        ("schema", "WRONG"), ("schema", "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V13"), ("schema", "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V13"), ("schema", "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V13"),
        ("approved_implementation_sha", "WRONG"),
        ("protocol_v7_sha", "WRONG"),
        ("seal_v2_sha", "WRONG"),
        ("label_scientific_sha", "WRONG"),
        ("runtime_v3_identity", "WRONG"),
        ("runtime_v3_pin_sha", "WRONG"),
        ("nominal_root_population_digest", "WRONG"),
        ("validation_population_digest", "WRONG"),
        ("test_population_digest", "WRONG"),
        ("test_root_ids", ("WRONG",))
    ]
    for k, v in mutations:
        r = valid_res.copy()
        r[k] = v
        with pytest.raises(ValueError):
            cp.validate_completed_worker_results(specs, [r])



def _large_payload_worker(spec):
    return {"data": "x" * (5 * 1024 * 1024)}

def test_large_payload_scheduler():
    import chessheat.cp_representation_efficiency as cp
    
    specs = [cp.JobSpec("C", 1, 1, ["r"], "nd", ["v"], "vd", ["t"], "td", "b", "c", "d", "e", "f", "a", "")]
    
    results = cp.run_job_specs(specs, _large_payload_worker)
    assert len(results) == 1
    assert len(results[0]["data"]) == 5 * 1024 * 1024

# ==============================================================================
# V14 HOSTILE PROOFS
# ==============================================================================
import sys
import time
import os

def _worker_raises(spec):
    raise ValueError("worker error")

def _worker_exits(spec):
    sys.exit(0)

def _worker_hangs(spec):
    time.sleep(10)

def test_scheduler_child_raises():
    import chessheat.cp_representation_efficiency as cp
    import pytest
    specs = [cp.JobSpec("C", 1, 1, ["r"], "nd", ["v"], "vd", ["t"], "td", "b", "c", "d", "e", "f", "a", "")]
    with pytest.raises(ValueError, match="worker error"):
        cp.run_job_specs(specs, _worker_raises)

def test_scheduler_child_exits_without_result():
    import chessheat.cp_representation_efficiency as cp
    import pytest
    specs = [cp.JobSpec("C", 1, 1, ["r"], "nd", ["v"], "vd", ["t"], "td", "b", "c", "d", "e", "f", "a", "")]
    with pytest.raises(RuntimeError, match="Process died without returning a result"):
        cp.run_job_specs(specs, _worker_exits)

def test_scheduler_child_hangs():
    import chessheat.cp_representation_efficiency as cp
    import pytest
    specs = [cp.JobSpec("C", 1, 1, ["r"], "nd", ["v"], "vd", ["t"], "td", "b", "c", "d", "e", "f", "a", "")]
    with pytest.raises(RuntimeError, match="Worker watchdog timeout exceeded"):
        cp.run_job_specs(specs, _worker_hangs, watchdog_timeout=1.0)


def test_root_weighted_numerical_hostile_proof():
    import subprocess
    import sys
    import os
    import json
    
    script = '''
import chessheat.ml_runtime as ml
ml.validate_runtime_identity = lambda: None
import chessheat.cp_representation_efficiency as cp
import torch
import json

def make_root(rid, n_pairs):
    import hashlib
    from chessheat.cp_target_labels import SourcePairFeatures
    return {
        "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
        "root_identity": rid,
        "label_derivation_protocol": "CP_TARGET_LABEL_DERIVATION_V6",
        "target_evaluator_version": "16.1",
        "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
        "partition": "TRAIN",
        "sufficient_position": {
            "board_arrangement_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            "side_to_move": "w",
            "castling_rights": "KQkq",
            "ep_square": None
        },
        "target_evaluable_pair_count": n_pairs,
        "target_non_evaluable_pair_count": 0,
        "source_pair_count": n_pairs,
        "pairs": [
            {
                "pair_id": hashlib.sha256(f"CHESSHEAT_TARGET_PAIR_V1|{rid}|a1{chr(97+i)}1|e7e5".encode()).hexdigest(),
                "m1_uci": f"a1{chr(97+i)}1", "m2_uci": "e7e5",
                "source_cp_m1": 100, "source_cp_m2": -50,
                "d_X": SourcePairFeatures(f"a1{chr(97+i)}1", 100, "e7e5", -50).d_x,
                "a_X": SourcePairFeatures(f"a1{chr(97+i)}1", 100, "e7e5", -50).a_x,
                "target_label": "FIRST_BETTER",
                "m1_heat": 0.5, "m2_heat": -0.5
            } for i in range(n_pairs)
        ]
    }

class MockLoss(torch.nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()
    def forward(self, logits, target):
        n = target.shape[0]
        if n == 1:
            t = torch.tensor([10.0], requires_grad=True)
        elif n == 5:
            t = torch.tensor([2.0, 2.0, 2.0, 2.0, 2.0], requires_grad=True)
        else:
            t = torch.zeros(n, requires_grad=True)
        return t

step_counts = []
def mock_build_adam(*args, **kwargs):
    class MockOpt:
        def zero_grad(self): pass
        def step(self): step_counts.append(1)
    return MockOpt()

def mock_evaluate(*args, **kwargs):
    raise StopIteration("Stop epoch")

backward_scalars = []
original_backward = torch.Tensor.backward
def mock_backward(self, *args, **kwargs):
    backward_scalars.append(self.item())

torch.Tensor.backward = mock_backward
cp.build_frozen_adam = mock_build_adam
torch.nn.CrossEntropyLoss = MockLoss
cp.evaluate_roots = mock_evaluate

train = [make_root(f"CHESSHEAT_TARGET_ROOT_{i}", 1 if i % 2 == 0 else 5) for i in range(250)]
train.sort(key=lambda x: cp.canonical_budget_order(x["root_identity"]))
val = [make_root("CHESSHEAT_TARGET_ROOT_v1", 1)]
val[0]["partition"] = "VALIDATION"
test = [make_root("CHESSHEAT_TARGET_ROOT_te1", 1)]
test[0]["partition"] = "TEST"

original_get_epoch_order = cp.get_epoch_order
def run_with_counts(n_train):
    backward_scalars.clear()
    step_counts.clear()
    def mock_get_epoch_order(seed, epoch, root_ids):
        return root_ids[:n_train]
    cp.get_epoch_order = mock_get_epoch_order
    try:
        cp.run_training_job(
            condition="mu_D", nominal_budget=250, seed=1729,
            training_root_records=train, validation_root_records=val, test_root_records=test,
            nominal_root_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in train]),
            validation_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in val]),
            test_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in test])
        )
    except StopIteration:
        pass
    return list(backward_scalars), len(step_counts)

res_2, steps_2 = run_with_counts(2)

counts_map = {1: 1, 63: 1, 64: 1, 65: 2, 128: 2, 129: 3}
steps_out = {}
for n, expected in counts_map.items():
    _, s = run_with_counts(n)
    steps_out[n] = s

print(json.dumps({
    "backward_scalars_2": res_2,
    "steps": steps_out
}))
'''
    env = os.environ.copy()
    env["CHESSHEAT_RUNTIME_V3_AUTHORIZED"] = "1"
    env["CHESSHEAT_ML_RUNTIME_ID"] = "CHESSHEAT_ML_RUNTIME_V3"
    env["CHESSHEAT_MPS_ENABLED"] = "0"
    
    p = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip())
    
    scalars = out["backward_scalars_2"]
    assert len(scalars) == 1
    # root A=10, root B=2. Expected root-weighted mean = 6.0
    expected = 6.0
    global_mean = (10.0 + 2.0*5) / 6
    assert abs(scalars[0] - expected) < 1e-5
    assert abs(scalars[0] - global_mean) > 1.0
    
    steps = out["steps"]
    expected_steps = {"1": 1, "63": 1, "64": 1, "65": 2, "128": 2, "129": 3}
    for k, v in expected_steps.items():
        assert steps[str(k)] == v

def test_early_stopping_hostile_proof():
    import subprocess
    import sys
    import os
    import json
    
    script = '''
import chessheat.ml_runtime as ml
ml.validate_runtime_identity = lambda: None
import chessheat.cp_representation_efficiency as cp
import torch
import json

def make_root(rid, n_pairs):
    import hashlib
    from chessheat.cp_target_labels import SourcePairFeatures
    return {
        "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
        "root_identity": rid,
        "label_derivation_protocol": "CP_TARGET_LABEL_DERIVATION_V6",
        "target_evaluator_version": "16.1",
        "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
        "partition": "TRAIN",
        "sufficient_position": {
            "board_arrangement_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            "side_to_move": "w",
            "castling_rights": "KQkq",
            "ep_square": None
        },
        "target_evaluable_pair_count": n_pairs,
        "target_non_evaluable_pair_count": 0,
        "source_pair_count": n_pairs,
        "pairs": [
            {
                "pair_id": hashlib.sha256(f"CHESSHEAT_TARGET_PAIR_V1|{rid}|a1{chr(97+i)}1|e7e5".encode()).hexdigest(),
                "m1_uci": f"a1{chr(97+i)}1", "m2_uci": "e7e5",
                "source_cp_m1": 100, "source_cp_m2": -50,
                "d_X": SourcePairFeatures(f"a1{chr(97+i)}1", 100, "e7e5", -50).d_x,
                "a_X": SourcePairFeatures(f"a1{chr(97+i)}1", 100, "e7e5", -50).a_x,
                "target_label": "FIRST_BETTER",
                "m1_heat": 0.5, "m2_heat": -0.5
            } for i in range(n_pairs)
        ]
    }

def mock_build_adam(*args, **kwargs):
    class MockOpt:
        def zero_grad(self): pass
        def step(self): pass
    return MockOpt()

original_eval = cp.evaluate_roots
val_seq = []
epoch_idx = 0
def mock_evaluate(*args, **kwargs):
    global epoch_idx
    if epoch_idx < len(val_seq):
        val = val_seq[epoch_idx]
    else:
        val = 100.0
    epoch_idx += 1
    return {"CHESSHEAT_TARGET_ROOT_val1": val}

cp.build_frozen_adam = mock_build_adam
cp.evaluate_roots = mock_evaluate
original_build_model = cp._build_model
def mock_build_model(*args, **kwargs):
    class M(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.p = torch.nn.Parameter(torch.zeros(1))
        def forward(self, x, y):
            return torch.zeros(x.shape[0], 3, device=x.device) + self.p.to(x.device)
    return M()
cp._build_model = mock_build_model

train = [make_root(f"CHESSHEAT_TARGET_ROOT_tr{i}", 1) for i in range(250)]
train.sort(key=lambda x: cp.canonical_budget_order(x["root_identity"]))
val = [make_root("CHESSHEAT_TARGET_ROOT_val1", 1)]
val[0]["partition"] = "VALIDATION"
test = [make_root("CHESSHEAT_TARGET_ROOT_test1", 1)]
test[0]["partition"] = "TEST"

def run_seq(seq):
    global val_seq, epoch_idx
    val_seq = seq
    epoch_idx = 0
    try:
        res = cp.run_training_job(
            condition="mu_D", nominal_budget=250, seed=1729,
            training_root_records=train, validation_root_records=val, test_root_records=test,
            nominal_root_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in train]),
            validation_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in val]),
            test_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in test])
        )
        return {"status": "ok", "best": res["best_epoch"], "epochs": res["epochs_completed"]}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

out = {}
out["strict_improve"] = run_seq([10.0, 9.0, 8.0, 7.0] + [100.0]*20)
out["equal_no_improve"] = run_seq([10.0, 10.0, 10.0] + [100.0]*20)
out["nan"] = run_seq([float('nan')])
out["inf"] = run_seq([float('inf')])
out["ninf"] = run_seq([float('-inf')])
out["never_stop"] = run_seq([200.0 - i for i in range(250)])

print(json.dumps(out))
'''
    env = os.environ.copy()
    env["CHESSHEAT_RUNTIME_V3_AUTHORIZED"] = "1"
    env["CHESSHEAT_ML_RUNTIME_ID"] = "CHESSHEAT_ML_RUNTIME_V3"
    env["CHESSHEAT_MPS_ENABLED"] = "0"
    
    p = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip())
    
    assert out["strict_improve"].get("status") == "ok", out["strict_improve"]
    assert out["strict_improve"]["best"] == 3
    assert out["strict_improve"]["epochs"] == 3 + 20 + 1 # wait, it runs epoch 3 (the best), then 20 more epochs of failure, total 24 epochs!
    assert out["equal_no_improve"]["best"] == 0
    assert out["nan"]["status"] == "error"
    assert out["inf"]["status"] == "error"
    assert out["ninf"]["status"] == "error"
    assert out["never_stop"]["best"] == 199
    assert out["never_stop"]["epochs"] == 200

def test_model_state_digest_hostile_proof():
    import chessheat.cp_representation_efficiency as cp
    import torch
    import copy
    
    model = cp._build_model(torch)
    d1 = cp.get_canonical_state_digest(model)
    d2 = cp.get_canonical_state_digest(model)
    assert d1 == d2
    
    # save genuine model state
    saved_state = copy.deepcopy(model.state_dict())
    
    # single tensor value mutation
    with torch.no_grad():
        for name, param in model.named_parameters():
            param.data[0] += 1.0
            break
    d_val_mut = cp.get_canonical_state_digest(model)
    assert d_val_mut != d1
    
    # restore saved state
    model.load_state_dict(saved_state)
    assert cp.get_canonical_state_digest(model) == d1
    
    # state_dict parameter key/name mutation
    state = copy.deepcopy(saved_state)
    keys = list(state.keys())
    state["wrong_key_name"] = state.pop(keys[0])
    model_mock = torch.nn.Module()
    model_mock.state_dict = lambda: state
    d_key_mut = cp.get_canonical_state_digest(model_mock)
    assert d_key_mut != d1
    
    # tensor shape mutation
    state = copy.deepcopy(saved_state)
    state[keys[0]] = state[keys[0]].view(-1)
    d_shape_mut = cp.get_canonical_state_digest(model_mock)
    assert d_shape_mut != d1
    
    # tensor dtype mutation
    state = copy.deepcopy(saved_state)
    state[keys[0]] = state[keys[0]].to(torch.float64)
    d_dtype_mut = cp.get_canonical_state_digest(model_mock)
    assert d_dtype_mut != d1

def test_checkpoint_test_once_proof():
    import subprocess
    import sys
    import os
    import json

    script = """
import chessheat.ml_runtime as ml
ml.validate_runtime_identity = lambda: None
import chessheat.cp_representation_efficiency as cp
import torch
import json

def make_root(rid, n_pairs):
    import hashlib
    from chessheat.cp_target_labels import SourcePairFeatures
    return {
        "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
        "root_identity": rid,
        "label_derivation_protocol": "CP_TARGET_LABEL_DERIVATION_V6",
        "target_evaluator_version": "16.1",
        "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
        "partition": "TRAIN",
        "sufficient_position": {
            "board_arrangement_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
            "side_to_move": "w",
            "castling_rights": "KQkq",
            "ep_square": None
        },
        "target_evaluable_pair_count": n_pairs,
        "target_non_evaluable_pair_count": 0,
        "source_pair_count": n_pairs,
        "pairs": [
            {
                "pair_id": hashlib.sha256(f"CHESSHEAT_TARGET_PAIR_V1|{rid}|a1{chr(97+i)}1|e7e5".encode()).hexdigest(),
                "m1_uci": f"a1{chr(97+i)}1", "m2_uci": "e7e5",
                "source_cp_m1": 100, "source_cp_m2": -50,
                "d_X": SourcePairFeatures(f"a1{chr(97+i)}1", 100, "e7e5", -50).d_x,
                "a_X": SourcePairFeatures(f"a1{chr(97+i)}1", 100, "e7e5", -50).a_x,
                "target_label": "FIRST_BETTER",
                "m1_heat": 0.5, "m2_heat": -0.5
            } for i in range(n_pairs)
        ]
    }

def mock_build_adam(*args, **kwargs):
    class MockOpt:
        def zero_grad(self): pass
        def step(self): pass
    return MockOpt()
cp.build_frozen_adam = mock_build_adam

events = []
selected_best_sha = None
restored_best_sha = None

original_eval = cp.evaluate_roots
def mock_evaluate(model, root_records_tensors, root_ids, torch):
    if root_ids and "CHESSHEAT_TARGET_ROOT_test1" in root_ids:
        events.append("TEST_EVALUATION")
    return original_eval(model, root_records_tensors, root_ids, torch)
cp.evaluate_roots = mock_evaluate

original_get_canonical = cp.get_canonical_state_digest
def mock_get_canonical(model):
    global selected_best_sha
    d = original_get_canonical(model)
    if "LOAD_STATE_DICT_BEST" not in events:
        events.append("BEST_SELECTED")
        selected_best_sha = d
    return d
cp.get_canonical_state_digest = mock_get_canonical

original_build_model = cp._build_model
def mock_build_model(*args, **kwargs):
    model = original_build_model(*args, **kwargs)
    original_load = model.load_state_dict
    def mock_load(state_dict):
        original_load(state_dict)
        events.append("LOAD_STATE_DICT_BEST")
        global restored_best_sha
        restored_best_sha = original_get_canonical(model)
    model.load_state_dict = mock_load
    return model
cp._build_model = mock_build_model

train = [make_root(f"CHESSHEAT_TARGET_ROOT_tr{i}", 1) for i in range(250)]
train.sort(key=lambda x: cp.canonical_budget_order(x["root_identity"]))
val = [make_root("CHESSHEAT_TARGET_ROOT_val1", 1)]
val[0]["partition"] = "VALIDATION"
test = [make_root("CHESSHEAT_TARGET_ROOT_test1", 1)]
test[0]["partition"] = "TEST"

res = cp.run_training_job(
    condition="mu_D", nominal_budget=250, seed=1729,
    training_root_records=train, validation_root_records=val, test_root_records=test,
    nominal_root_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in train]),
    validation_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in val]),
    test_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in test])
)

print(json.dumps({
    "events": events,
    "selected_best_sha": selected_best_sha,
    "restored_best_sha": restored_best_sha,
    "final_digest": res["canonical_model_state_sha"]
}))
"""
    env = os.environ.copy()
    env["CHESSHEAT_RUNTIME_V3_AUTHORIZED"] = "1"
    env["CHESSHEAT_ML_RUNTIME_ID"] = "CHESSHEAT_ML_RUNTIME_V3"

    p = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip())
    events = out["events"]
    assert "BEST_SELECTED" in events
    assert "LOAD_STATE_DICT_BEST" in events
    assert "TEST_EVALUATION" in events
    # order
    idx_best = events.index("BEST_SELECTED")
    idx_load = events.index("LOAD_STATE_DICT_BEST")
    idx_test = events.index("TEST_EVALUATION")
    assert idx_best < idx_load < idx_test
    assert events.count("TEST_EVALUATION") == 1
    assert out["selected_best_sha"] == out["restored_best_sha"]

def test_four_condition_information_boundary():
    import chessheat.cp_representation_efficiency as cp
    from chessheat.cp_target_labels import SourcePairFeatures
    import hashlib
    
    m1 = "e2e4"
    m2 = "e7e5"
    expected_sha = hashlib.sha256(f"CHESSHEAT_TARGET_PAIR_V1|root_1|{m1}|{m2}".encode()).hexdigest()
    
    synthetic_root = {
        "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
        "root_identity": "root_1",
        "label_derivation_protocol": "CP_TARGET_LABEL_DERIVATION_V6",
        "target_evaluator_version": "16.1",
        "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
        "partition": "TRAIN",
        "target_label": 0.5,
        "sufficient_position": {
                "board_arrangement_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
                "side_to_move": "w",
                "castling_rights": "KQkq",
                "ep_square": None
            },
        "target_evaluable_pair_count": 1,
        "target_non_evaluable_pair_count": 0,
        "source_pair_count": 1,
        "pairs": [
            {
                "pair_id": expected_sha,
                "m1_uci": m1,
                "m2_uci": m2,
                "source_cp_m1": 100,
                "source_cp_m2": -50,
                "d_X": SourcePairFeatures("e2e4", 100, "e7e5", -50).d_x,
                "a_X": SourcePairFeatures("e2e4", 100, "e7e5", -50).a_x,
                "target_label": "FIRST_BETTER",
                "m1_heat": 0.5,
                "m2_heat": -0.5
            }
        ]
    }
    
    rec_muD = cp.construct_learner_records(synthetic_root, "mu_D")
    rec_muT = cp.construct_learner_records(synthetic_root, "mu_T")
    rec_BdaS = cp.construct_learner_records(synthetic_root, "B_daS")
    rec_Bperm = cp.construct_learner_records(synthetic_root, "B_perm")
    
    assert len(rec_muD) == 1
    assert len(rec_muT) == 1
    assert len(rec_BdaS) == 1
    assert len(rec_Bperm) == 1
    
    # Require byte-identical p_tensor, side_tensor, label
    assert rec_muD[0].p_tensor.to_bytes() == rec_muT[0].p_tensor.to_bytes() == rec_BdaS[0].p_tensor.to_bytes() == rec_Bperm[0].p_tensor.to_bytes()
    assert rec_muD[0].side_tensor.to_bytes() == rec_muT[0].side_tensor.to_bytes() == rec_BdaS[0].side_tensor.to_bytes() == rec_Bperm[0].side_tensor.to_bytes()
    assert rec_muD[0].label == rec_muT[0].label == rec_BdaS[0].label == rec_Bperm[0].label
    
    # Require B_daS spatial_map == canonical all-zero 1x8x8 float32 map
    zero_map = [0.0] * 64
    import struct
    zero_bytes = struct.pack('<64f', *zero_map)
    assert rec_BdaS[0].spatial_map.to_bytes() == zero_bytes
    
    # Require mu_D spatial_map == build_m_d
    sf = SourcePairFeatures(m1, 100, m2, -50)
    assert rec_muD[0].spatial_map.to_bytes() == cp.build_m_d(sf).to_bytes()
    
    # Require mu_T spatial_map == build_m_t
    assert rec_muT[0].spatial_map.to_bytes() == cp.build_m_t(sf).to_bytes()
    
    # Require B_perm spatial_map == build_m_perm
    assert rec_Bperm[0].spatial_map.to_bytes() == cp.build_m_perm(sf).to_bytes()

def test_b_perm_primary_analysis_exclusion():
    import copy
    import os
    import json
    from unittest.mock import patch
    import chessheat.cp_representation_efficiency as cp

    def fake_res(condition):
        return {
            "schema": "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V14",
            "condition": condition,
            "nominal_budget": 250,
            "seed": 1729,
            "runtime_v3_identity": "CHESSHEAT_ML_RUNTIME_V3",
            "runtime_v3_pin_sha": "fake",
            "nominal_root_population_digest": "fake",
            "effective_root_population_digest": "fake",
            "validation_population_digest": "fake",
            "test_population_digest": "fake",
            "epochs_completed": 10,
            "best_epoch": 9,
            "validation_trace": [0.0]*10,
            "canonical_model_state_sha": "fake",
            "test_root_ids": ["root1", "root2"],
            "test_root_losses": {"root1": 0.5, "root2": 0.6}
        }

    results = []
    for cond in ["mu_D", "mu_T", "B_daS", "B_perm"]:
        for b in [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]:
            for s in [1729, 2718, 31415, 65537, 104729]:
                r = fake_res(cond)
                r["nominal_budget"] = b
                r["seed"] = s
                results.append(r)

    results_X = copy.deepcopy(results)
    results_Y = copy.deepcopy(results)
    for r in results_Y:
        if r["condition"] == "B_perm":
            r["test_root_losses"]["root1"] += 100.0
            r["test_root_losses"]["root2"] += 100.0

    seen_keys = []
    original_bootstrap = cp.full_bootstrap_procedure
    def mock_bootstrap(test_root_ids, mean_nlls):
        seen_keys.append(list(mean_nlls.keys()))
        return original_bootstrap(test_root_ids, mean_nlls)

    os.environ["CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED"] = "CHESSHEAT_SCIENTIFIC_ANALYSIS_V1_AUTHORIZED"
    try:
        with patch("chessheat.cp_representation_efficiency.full_bootstrap_procedure", mock_bootstrap):
            out_X = cp.run_scientific_analysis(results_X)
            out_Y = cp.run_scientific_analysis(results_Y)
    finally:
        del os.environ["CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED"]

    assert len(seen_keys) == 2
    assert set(seen_keys[0]) == {"mu_D", "mu_T", "B_daS"}
    assert set(seen_keys[1]) == {"mu_D", "mu_T", "B_daS"}

    assert out_X["ci_results"]["Delta_DT"] == out_Y["ci_results"]["Delta_DT"]
    assert out_X["ci_results"]["Delta_D0"] == out_Y["ci_results"]["Delta_D0"]
    assert out_X["ci_results"]["Delta_T0"] == out_Y["ci_results"]["Delta_T0"]
    assert out_X["outcome"] == out_Y["outcome"]
    assert out_X["AULC_D"] == out_Y["AULC_D"]
    assert out_X["AULC_T"] == out_Y["AULC_T"]
    assert out_X["AULC_BdaS"] == out_Y["AULC_BdaS"]
    assert out_X["ci_results"] == out_Y["ci_results"]

def test_max_pair_mps_feasibility():
    import sys
    import platform
    import subprocess
    import os

    if not (sys.platform == "darwin" and platform.machine() == "arm64"):
        return

    script = '''
import os
import chessheat.ml_runtime as ml
ctx = ml.configure_runtime(1729)

import torch
from chessheat.cp_representation_efficiency import _build_model, initialize_model_cpu_then_mps

model = initialize_model_cpu_then_mps(_build_model, ctx)
loss_fn = torch.nn.CrossEntropyLoss(reduction='none')

spatial = torch.randn(23653, 19, 8, 8, device=ctx.device)
side = torch.randn(23653, 270, device=ctx.device)
labels = torch.zeros(23653, dtype=torch.long, device=ctx.device)

logits = model(spatial, side)
loss = loss_fn(logits, labels).mean()
loss.backward()
print("MAX_PAIR_MPS_FEASIBILITY_PASS")
'''
    env = os.environ.copy()
    env["CHESSHEAT_RUNTIME_V3_AUTHORIZED"] = "1"
    env["CHESSHEAT_MPS_ENABLED"] = "1"
    env["CHESSHEAT_ALLOW_CPU_FALLBACK"] = "0"
    env["CHESSHEAT_ML_RUNTIME_ID"] = "CHESSHEAT_ML_RUNTIME_V3"
    env["CHESSHEAT_MPS_ENABLED"] = "0"
    env["PYTHONHASHSEED"] = "0"
    env["PYTORCH_MPS_FAST_MATH"] = "0"
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
    env["PYTORCH_MPS_PREFER_METAL"] = "0"

    p = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    if "MAX_PAIR_MPS_FEASIBILITY_PASS" not in p.stdout:
        print("STDOUT:", p.stdout)
        print("STDERR:", p.stderr)
        raise RuntimeError("MPS feasibility failed")

def test_fresh_process_determinism():
    import sys
    import subprocess
    import os
    
    script = '''
import json
import os
import chessheat.cp_representation_efficiency as cp
from chessheat.cp_target_labels import SourcePairFeatures

def main():
    def make_root(rid, partition):
        import hashlib
        m1 = "e2e4"
        m2 = "e7e5"
        expected_sha = hashlib.sha256(f"CHESSHEAT_TARGET_PAIR_V1|{rid}|{m1}|{m2}".encode()).hexdigest()
        sf = SourcePairFeatures(m1, 100, m2, -50)
        
        return {
            "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
            "root_identity": rid,
            "label_derivation_protocol": "CP_TARGET_LABEL_DERIVATION_V6",
            "target_evaluator_version": "16.1",
            "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
            "partition": partition,
            "sufficient_position": {
                "board_arrangement_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
                "side_to_move": "w",
                "castling_rights": "KQkq",
                "ep_square": None
            },
            "target_evaluable_pair_count": 1,
            "target_non_evaluable_pair_count": 0,
            "source_pair_count": 1,
            "pairs": [
                {
                    "pair_id": expected_sha,
                    "m1_uci": m1,
                    "m2_uci": m2,
                    "source_cp_m1": 100,
                    "source_cp_m2": -50,
                    "d_X": sf.d_x,
                    "a_X": sf.a_x,
                    "target_label": "FIRST_BETTER",
                    "m1_heat": 0.5,
                    "m2_heat": -0.5
                }
            ]
        }
    
    train = [make_root(f"CHESSHEAT_TARGET_ROOT_{i}", "TRAIN") for i in range(250)]
    train.sort(key=lambda x: cp.canonical_budget_order(x["root_identity"]))
    val = [make_root(f"v_{i}", "VALIDATION") for i in range(2)]
    test = [make_root(f"te_{i}", "TEST") for i in range(2)]

    res = cp.run_training_job(
        condition="mu_D",
        nominal_budget=250,
        seed=1729,
        training_root_records=train,
        validation_root_records=val,
        test_root_records=test,
        nominal_root_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in train]),
        validation_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in val]),
        test_population_digest=cp.canonical_root_population_digest([r["root_identity"] for r in test])
    )

    print(json.dumps({
        "condition": res["condition"],
        "nominal_budget": res["nominal_budget"],
        "seed": res["seed"],
        "nominal_root_population_digest": res["nominal_root_population_digest"],
        "effective_root_population_digest": res["effective_root_population_digest"],
        "validation_population_digest": res["validation_population_digest"],
        "test_population_digest": res["test_population_digest"],
        "epochs_completed": res["epochs_completed"],
        "best_epoch": res["best_epoch"],
        "validation_trace": res["validation_trace"],
        "canonical_model_state_sha": res["canonical_model_state_sha"],
        "test_root_ids": res["test_root_ids"],
        "test_root_losses": res["test_root_losses"]
    }))

if __name__ == "__main__":
    main()
'''
    env = os.environ.copy()
    env["CHESSHEAT_RUNTIME_V3_AUTHORIZED"] = "1"
    env["CHESSHEAT_MPS_ENABLED"] = "1"
    env["CHESSHEAT_ALLOW_CPU_FALLBACK"] = "0"
    env["CHESSHEAT_ML_RUNTIME_ID"] = "CHESSHEAT_ML_RUNTIME_V3"
    env["CHESSHEAT_MPS_ENABLED"] = "0"
    env["PYTHONHASHSEED"] = "0"
    env["PYTORCH_MPS_FAST_MATH"] = "0"
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
    env["PYTORCH_MPS_PREFER_METAL"] = "0"
    
    p1 = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    p2 = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    
    assert p1.returncode == 0, p1.stderr
    assert p2.returncode == 0, p2.stderr
    
    import json
    out1 = json.loads(p1.stdout.strip().splitlines()[-1])
    out2 = json.loads(p2.stdout.strip().splitlines()[-1])
    
    assert out1 == out2
