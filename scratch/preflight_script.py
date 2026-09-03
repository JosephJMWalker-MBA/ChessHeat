import sys
import os
import json
import hashlib
from collections import defaultdict
import subprocess

sys.path.append("src")
from chessheat.cp_representation_efficiency import (
    verify_training_evidence_preflight,
    DerivedCache,
    build_frozen_populations,
    build_job_specs
)

def run_preflight():
    artifact = {
        "schema": "CP_REPRESENTATION_EFFICIENCY_PRODUCTION_PREFLIGHT_V1",
        "approved_implementation_sha": "82b8da2285d5bf48cbd27bd1f30388c79e92f347",
        "authoritative_audit_sha": "47efbe7241986b5a20c9b5031d5934358cfdd2dd",
        "protocol_v7_sha": "ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef",
        "label_scientific_sha": "c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2",
        "Runtime_V3_identity": "CHESSHEAT_ML_RUNTIME_V3",
        "real_training_count": 0,
        "scientific_july_analysis_performed": False,
        "failure_classes": []
    }
    
    try:
        ev = verify_training_evidence_preflight("82b8da2285d5bf48cbd27bd1f30388c79e92f347")
        artifact["evidence_preflight"] = "PASS"
    except Exception as e:
        artifact["evidence_preflight"] = f"FAIL: {e}"
        artifact["failure_classes"].append("EVIDENCE_PREFLIGHT_FAIL")
        
    try:
        env = os.environ.copy()
        env["CHESSHEAT_ML_RUNTIME_ID"] = "CHESSHEAT_ML_RUNTIME_V3"
        env["CHESSHEAT_REPO_ROOT"] = "/Users/josephjmwalker-mba/Documents/GitHub/Chess-Board-Heat-Map-Instruct"
        env["PYTHONHASHSEED"] = "0"
        env["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        env["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
        env["PYTORCH_MPS_FAST_MATH"] = "0"
        env["PYTORCH_MPS_PREFER_METAL"] = "0"
        env["OMP_NUM_THREADS"] = "1"
        env["OPENBLAS_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["VECLIB_MAXIMUM_THREADS"] = "1"
        env["NUMEXPR_NUM_THREADS"] = "1"
        res = subprocess.run(
            ['.venv/bin/python3', "-c", "import sys; sys.path.append('src'); from chessheat.ml_runtime import validate_runtime_identity; print(validate_runtime_identity())"],
            env=env, capture_output=True, text=True
        )
        if res.returncode == 0:
            artifact["runtime_preflight"] = "PASS"
        else:
            artifact["runtime_preflight"] = f"FAIL: {res.stderr}"
            artifact["failure_classes"].append("RUNTIME_V3_VALIDATION_FAIL")
    except Exception as e:
        artifact["runtime_preflight"] = f"FAIL: {e}"
        
    artifact["output_persistence"] = {
        "present": False,
        "mechanism": "None. Parent keeps workers' dicts in memory and returns them.",
        "crash_safety": "None. Parent crash loses all worker results.",
        "result_sealing": "Result is sealed in memory, but not durably persisted.",
        "resumption_semantics": "RESUMPTION_SEMANTICS_UNDEFINED. No durable journal exists."
    }
    artifact["failure_classes"].append("NO_DURABLE_WORKER_RESULT_SEAL")
    artifact["output_persistence_absent"] = True
    
    import shutil
    total, used, free = shutil.disk_usage(".")
    artifact["storage"] = {
        "available_bytes": free,
        "estimated_required_bytes": 160 * 200 * 1024 
    }
    
    cache_path = "artifacts/research/cp_target_labels_2026_07/cp_target_pair_labels_v6.jsonl"
    artifact["cache"] = {
        "path": cache_path,
        "SHA": "c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2"
    }
    try:
        cache = DerivedCache(cache_path, "c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2")
        artifact["cache"]["status"] = "LOADED"
    except Exception as e:
        artifact["cache"]["status"] = f"FAIL: {e}"
        artifact["failure_classes"].append("CANONICAL_CACHE_ABSENT")
        artifact["verdict"] = "PRODUCTION_DOWNSTREAM_TRAINING_EXECUTION_PREFLIGHT_FAIL"
        
        with open("artifacts/research/CP_REPRESENTATION_EFFICIENCY_PRODUCTION_PREFLIGHT_V1.json", "w") as f:
            json.dump(artifact, f, indent=2)
        return

if __name__ == "__main__":
    run_preflight()
    print("DONE")
