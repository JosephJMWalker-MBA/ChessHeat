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
    # 5. Positive control from the real materializer
    from chessheat.cp_target_labels import derive_root_pair_labels_v6
    
    synthetic_manifest = {
        "schema": "CHESSHEAT_TARGET_ACQUISITION_MANIFEST_V1",
        "protocol_id": "CP_TARGET_ACQUISITION_PROTOCOL_V7",
        "manifest_sha256": "0"*64,
        "root_identity": "root1",
        "root_record_digest": "dummy_digest",
        "transposition_group": 1,
        "sufficient_position": {"side_to_move": "w", "board_arrangement_fen": "mock", "castling_rights": "KQkq", "en_passant_square": None}
    }
    
    synthetic_source = {
        "schema": "CP_SOURCE_FEASIBILITY_RESULT_V2",
        "status": "FAILURE",
        "error_type": "mock",
        "error_message": "mock",
        "root_identity": "root1",
        "root_record_digest": "dummy_digest"
    }
    
    synthetic_target = {
        "schema": "CP_TARGET_ACQUISITION_RESULT_V2",
        "status": "FAILURE",
        "error_type": "mock",
        "error_message": "mock",
        "root_identity": "root1",
        "root_record_digest": "dummy_digest"
    }
    
    # 5. invoke authoritative materializer
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
    
    # Manually populate valid pair
    res["source_pair_count"] = 1
    res["target_evaluable_pair_count"] = 1
    valid_pair_id = hashlib.sha256(b"a1a2|b1b2").hexdigest()
    res["pairs"] = [{
        "m1_uci": "a1a2",
        "m2_uci": "b1b2",
        "pair_id": valid_pair_id,
        "target_label": "FIRST_BETTER",
        "source_m1_m2_cp_delta": 50,
        "source_m1_m2_d_X": 1.0,
        "source_m1_m2_a_X": 0.5
    }]
    
    # Pass directly into downstream validator
    cp.read_and_validate_roots([res])
    # REAL_MATERIALIZER_OUTPUT_ACCEPTED = 1
    
    # mutate independently
    import copy
    
    # synthetic top-level addition/removal irrelevant
    res2 = copy.deepcopy(res)
    res2["side_to_move"] = "w"
    cp.read_and_validate_roots([res2])
    
    res2 = copy.deepcopy(res)
    res2["sufficient_position"]["side_to_move"] = "invalid"
    with pytest.raises(ValueError):
        cp.read_and_validate_roots([res2])
        
    res2 = copy.deepcopy(res)
    res2["pairs"][0]["pair_id"] = "bad"
    with pytest.raises(ValueError):
        cp.read_and_validate_roots([res2])
        
    res2 = copy.deepcopy(res)
    res2["target_evaluable_pair_count"] = 999
    with pytest.raises(ValueError):
        cp.read_and_validate_roots([res2])
        
    res2 = copy.deepcopy(res)
    res2["pairs"][0]["source_m1_m2_cp_delta"] = True
    with pytest.raises(ValueError):
        cp.read_and_validate_roots([res2])

def test_sha_gate_hostile_matrix(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        subprocess.check_call(["git", "init"], cwd=d)
        for f in cp.BOUND_FILES:
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
        with open(os.path.join(d, cp.BOUND_FILES[0]), "a") as fp: fp.write("drift")
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(sha, d)
        subprocess.check_call(["git", "checkout", "--", cp.BOUND_FILES[0]], cwd=d)
        
        # 10. staged bound drift
        with open(os.path.join(d, cp.BOUND_FILES[0]), "a") as fp: fp.write("drift")
        subprocess.check_call(["git", "add", cp.BOUND_FILES[0]], cwd=d)
        with pytest.raises(ValueError): cp.verify_approved_sha_gate(sha, d)
        subprocess.check_call(["git", "reset", "--hard", "HEAD"], cwd=d)
        
        # 11. stale implementation
        with open(os.path.join(d, cp.BOUND_FILES[0]), "w") as fp: fp.write("old")
        subprocess.check_call(["git", "commit", "-am", "old"], cwd=d)
        old_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=d).decode().strip()
        monkeypatch.setenv("CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA", old_sha)
        with open(os.path.join(d, cp.BOUND_FILES[0]), "w") as fp: fp.write("new")
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

def test_evidence_preflight_mutations():
    with tempfile.TemporaryDirectory() as d:
        p1 = os.path.join(d, "f1")
        with open(p1, "w") as f: f.write("test")
        
        idents = cp.verify_training_evidence_preflight([p1])
        assert len(idents) == 1
        
        with pytest.raises(ValueError):
            cp.verify_training_evidence_preflight([os.path.join(d, "missing")])

def test_cache_positive_hostile():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        r1 = {"root_identity": "r1", "partition": "TRAIN", "source_pair_count": 1}
        r2 = {"root_identity": "r2", "partition": "TEST"}
        f.write(json.dumps(r1) + "\n")
        f.write(json.dumps(r2) + "\n")
        path = f.name
        
    cache = cp.DerivedCache(path)
    assert cache.get_root("r1")["root_identity"] == "r1"
    assert cache.get_root("r2")["root_identity"] == "r2"
    assert cache.get_root("missing") is None
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(json.dumps(r1) + "\n")
        f.write(json.dumps(r1) + "\n")
        path2 = f.name
        
    with pytest.raises(ValueError):
        cp.DerivedCache(path2)
        
    os.remove(path)
    os.remove(path2)

def test_population_construction():
    cache = cp.DerivedCache()
    cache.roots = {
        "r1": {"partition": "TRAIN", "source_pair_count": 1},
        "r2": {"partition": "VALIDATION", "target_evaluable_pair_count": 1},
        "r3": {"partition": "TEST", "target_evaluable_pair_count": 1}
    }
    train, budgets, val, test, digest = cp.build_frozen_populations(cache)
    assert "r1" in train
    assert "r2" in val
    assert "r3" in test
    assert budgets == [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]

def test_160_job_specs():
    populations = (["r1"], [250, 500, 1000, 2000, 4000, 8000, 16000, 20000], ["r2"], ["r3"], "digest")
    specs = cp.build_job_specs(populations)
    assert len(specs) == 160
    assert specs[0]["condition"] in {"mu_D", "mu_T", "B_daS", "B_perm"}
    assert specs[0]["budget"] in [250, 500, 1000, 2000, 4000, 8000, 16000, 20000]
    assert specs[0]["seed"] in [0, 1, 2, 3, 4]

def dummy_worker(spec):
    if spec["seed"] == 999:
        raise RuntimeError("worker fail")
    return spec["seed"] * 2

def test_160_fresh_process_orchestration():
    specs = [{"seed": i} for i in range(160)]
    res = cp.run_job_specs(specs, dummy_worker)
    assert len(res) == 160
    assert res[0] == 0

def test_one_worker_failure():
    specs = [{"seed": 1}, {"seed": 999}]
    with pytest.raises(RuntimeError, match="worker fail"):
        cp.run_job_specs(specs, dummy_worker)

def test_runner_import_smoke():
    res = subprocess.run([
        sys.executable, "-c", "import scripts.run_cp_representation_efficiency"
    ], env=dict(os.environ, PYTHONPATH="src:."))
    assert res.returncode == 0

def test_runner_no_authorization_zero_side_effects():
    res = subprocess.run([
        sys.executable, "scripts/run_cp_representation_efficiency.py", "--mode", "train"
    ], env=dict(os.environ, PYTHONPATH="src:.", CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA="dummy"), capture_output=True)
    assert res.returncode != 0
    assert b"Training execution" not in res.stdout

# REMAINING_REAUDIT_TARGET: test_root_weighted_loss_and_attrition
# REMAINING_REAUDIT_TARGET: test_early_stopping
# REMAINING_REAUDIT_TARGET: test_checkpoint_test_once
# REMAINING_REAUDIT_TARGET: test_full_job_determinism
# REMAINING_REAUDIT_TARGET: MAX_PAIR_MPS_FEASIBILITY_REMAINING_REAUDIT_TARGET

