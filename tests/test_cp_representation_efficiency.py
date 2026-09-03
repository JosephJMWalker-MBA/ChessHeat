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
    cache.roots["v1"] = {"partition": "VALIDATION", "target_evaluable_pair_count": 1}
    cache.roots["t1"] = {"partition": "TEST", "target_evaluable_pair_count": 1}
    
    train, budgets, val, test, d_val, d_test, budget_digests = cp.build_frozen_populations(cache)
    assert len(train) == 20000
    assert "v1" in val
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
    val = ["v1"]
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
def test_worker_binding(monkeypatch):
    import chessheat.cp_representation_efficiency as cp
    
    class MockCache:
        def __init__(self, path, expected_sha):
            pass
        def get_root(self, rid):
            return {
                "schema": "CP_TARGET_PAIR_LABEL_ROOT_V6",
                "label_derivation_protocol": "CP_TARGET_LABEL_DERIVATION_V6",
                "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
                "partition": "TRAIN" if "r" in rid else ("VALIDATION" if "v" in rid else "TEST"),
                "root_identity": rid,
                "sufficient_position": {"side_to_move": "w"},
                "source_pair_count": 0,
                "pairs": []
            }
    
    monkeypatch.setattr(cp, "DerivedCache", MockCache)
    
    call_kwargs = []
    def spy_run_training_job(**kwargs):
        call_kwargs.append(kwargs)
        return {
            "schema": "CHESSHEAT_DOWNSTREAM_WORKER_RESULT_V11",
            "condition": kwargs["condition"],
            "nominal_budget": kwargs["nominal_budget"],
            "seed": kwargs["seed"],
            "nominal_root_count": len(kwargs["training_root_records"]),
            "nominal_root_population_digest": kwargs["nominal_root_population_digest"],
            "effective_training_root_count": len(kwargs["training_root_records"]),
            "effective_root_population_digest": "eff_digest",
            "validation_population_digest": kwargs["validation_population_digest"],
            "test_population_digest": kwargs["test_population_digest"],
            "best_epoch": 1,
            "best_validation_root_nll": 0.5,
            "epochs_completed": 1,
            "validation_trace": [],
            "test_evaluation_count": len(kwargs["test_root_records"]),
            "test_root_ids": tuple(r["root_identity"] for r in kwargs["test_root_records"]),
            "test_root_losses": [],
            "canonical_model_state_sha": "a"*64
        }
        
    monkeypatch.setattr(cp, "run_training_job", spy_run_training_job)
    
    class FakeSpec:
        cache_path = "cache_path"
        label_scientific_sha = "c"
        condition = "mu_D"
        nominal_budget = 250
        seed = 1729
        nominal_root_ids = tuple(["r1", "r2"])
        nominal_root_population_digest = cp.canonical_root_population_digest(nominal_root_ids)
        validation_root_ids = tuple(["v1"])
        validation_population_digest = cp.canonical_root_population_digest(validation_root_ids)
        test_root_ids = tuple(["t1"])
        test_population_digest = cp.canonical_root_population_digest(test_root_ids)
        approved_implementation_sha = "app_sha"
        protocol_v7_sha = "prot_sha"
        seal_v2_sha = "seal_sha"
        runtime_v3_identity = "CHESSHEAT_ML_RUNTIME_V3"
        runtime_v3_pin_sha = "rt_pin_sha"

    spec = FakeSpec()
    res = cp.run_downstream_worker(spec)
    
    assert len(call_kwargs) == 1
    assert call_kwargs[0]["condition"] == spec.condition
    assert call_kwargs[0]["nominal_budget"] == spec.nominal_budget
    assert call_kwargs[0]["seed"] == spec.seed
    
    assert res["approved_implementation_sha"] == "app_sha"
    
    # Mutate a digest
    spec.nominal_root_population_digest = "bad"
    call_kwargs.clear()
    import pytest
    with pytest.raises(ValueError):
        cp.run_downstream_worker(spec)
    assert len(call_kwargs) == 0

def test_parent_completeness_with_fake_worker(monkeypatch):
    import chessheat.cp_representation_efficiency as cp
    
    def mock_verify_approved(*args, **kwargs): pass
    def mock_check_auth(*args, **kwargs): pass
    
    class FakeEvId:
        label_scientific_sha = "c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2"
        protocol_v7_sha = "prot"
        seal_v2_sha = "seal"
        runtime_v3_pin_sha = "rt"
        
    def mock_preflight(*args, **kwargs): return FakeEvId()
    
    monkeypatch.setattr(cp, "verify_approved_sha_gate", mock_verify_approved)
    monkeypatch.setattr(cp, "check_real_training_authorization", mock_check_auth)
    monkeypatch.setattr(cp, "verify_training_evidence_preflight", mock_preflight)
    
    class FakeCache:
        def __init__(self, *args, **kwargs): pass
    monkeypatch.setattr(cp, "DerivedCache", FakeCache)
    
    def mock_populations(*args, **kwargs):
        train = ["r%d"%i for i in range(25000)]
        budgets = [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
        return train, budgets, ["v1"], ["t1"], "vd", "td", {b: str(b) for b in budgets}
    monkeypatch.setattr(cp, "build_frozen_populations", mock_populations)
    
    def mock_run_job_specs(specs, worker_fn):
        return [worker_fn(s) for s in specs]
    monkeypatch.setattr(cp, "run_job_specs", mock_run_job_specs)
    
    def fake_worker(spec):
        return {
            "condition": spec.condition,
            "nominal_budget": spec.nominal_budget,
            "seed": spec.seed
        }
    monkeypatch.setattr(cp, "run_downstream_worker", fake_worker)
    
    # 1. Exact 160 works
    res = cp.run_training_parent("app", "cache", "c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2")
    assert res == "STOP_BEFORE_SCIENTIFIC_ANALYSIS"
    
    # 2. Inject 159
    original_run_job_specs = cp.run_job_specs
    def mock_run_159(specs, worker):
        res = original_run_job_specs(specs, worker)
        return res[:-1]
    monkeypatch.setattr(cp, "run_job_specs", mock_run_159)
    import pytest
    with pytest.raises(ValueError, match="incompleteness"):
        cp.run_training_parent("app", "cache", "c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2")
        
    # 3. Inject duplicate
    def mock_run_dup(specs, worker):
        res = original_run_job_specs(specs, worker)
        return res + [res[0]]
    monkeypatch.setattr(cp, "run_job_specs", mock_run_dup)
    with pytest.raises(ValueError, match="incompleteness"):
        cp.run_training_parent("app", "cache", "c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2")

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
        
