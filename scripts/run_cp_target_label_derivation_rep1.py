#!/usr/bin/env python3
import os
import sys
import hashlib
import json
import datetime
import subprocess
from chessheat.cp_target_labels import TargetLabelMaterializerV6, FROZEN_JULY_2026_LABEL_EXPECTATIONS

MANIFEST_PATH = "artifacts/research/cp_source_feasibility_2026_07/cp_root_population_manifest_v2.jsonl.zst"
SOURCE_PATH = "artifacts/research/cp_source_feasibility_2026_07/raw/cp_source_root_results_v2.jsonl"
TARGET_PATH = "artifacts/research/cp_target_acquisition_2026_07/raw/cp_target_root_results_v2.jsonl"
OUTPUT_COMPRESSED_PATH = "artifacts/research/cp_target_labels_2026_07/cp_target_pair_labels_v7_rep1.jsonl.zst"
OUTPUT_UNCOMPRESSED_PATH = "artifacts/research/cp_target_labels_2026_07/cp_target_pair_labels_v7_rep1.jsonl"
SEAL_PATH = "artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v7_rep1.json"
PROTOCOL_PATH = "artifacts/research/cp_representation_efficiency_protocol_v7.json"

EXPECTED_PROTOCOL_SHA = "ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef"
EXPECTED_SOURCE_SHA = "9cfe28a13f185e207ac42c5708597b0577ef93f4fce29ca482e4e6a9c8d83774"
EXPECTED_TARGET_SHA = "d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00"
EXPECTED_TARGET_SEAL_SHA = "1f17ac7e27531d27bc050d49a8a1e60aa5e0ab53c26f28b2540f868c27a43dad"
EXPECTED_MANIFEST_SHA = "5a013e64265820b65d1d3687fcee98aa607ab41470294d11df7b2f803c8e063d"

def hash_file(path):
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()

def hash_manifest(path):
    import zstandard as zstd
    sha = hashlib.sha256()
    dctx = zstd.ZstdDecompressor()
    count = 0
    admitted = 0
    with open(path, "rb") as f:
        with dctx.stream_reader(f) as reader:
            buf = b""
            while True:
                chunk = reader.read(65536)
                if not chunk:
                    break
                sha.update(chunk)
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if line.strip():
                        count += 1
                        m_rec = json.loads(line)
                        if m_rec.get("inclusion") == "ADMITTED":
                            admitted += 1
            if buf != b"":
                raise ValueError("Unterminated final line in readback")
    return sha.hexdigest(), count, admitted

def check_approved_sha(sha_val):
    if not sha_val or len(sha_val) != 40 or not all(c in "0123456789abcdef" for c in sha_val):
        return False
    res = subprocess.run(["git", "cat-file", "-t", sha_val], capture_output=True, text=True)
    if res.returncode != 0 or res.stdout.strip() != "commit":
        return False
        
    bound_files = [
        "artifacts/research/target_label_derivation_runtime_pin_v1.json",
        "requirements/target-label-runtime-v1.txt",
        "src/chessheat/cp_target_labels.py",
        "src/chessheat/attribution.py",
        "src/chessheat/models.py",
        "src/chessheat/protocol_freeze.py",
        "src/chessheat/experiment.py",
        "src/chessheat/cp_root_population.py"
    ]
    
    # Check uncommitted changes in bound implementation files
    diff = subprocess.run(["git", "diff", "--quiet", "HEAD", "--"] + bound_files)
    if diff.returncode != 0:
        return False
        
    diff_staged = subprocess.run(["git", "diff", "--cached", "--quiet", "--"] + bound_files)
    if diff_staged.returncode != 0:
        return False
        
    # Check that HEAD tree matches the approved SHA tree for those files
    diff2 = subprocess.run(["git", "diff", "--quiet", sha_val, "HEAD", "--"] + bound_files)
    if diff2.returncode != 0:
        return False
        
    return True

def main():
    import zstandard as zstd
    print(f"Using zstandard: {zstd.__version__}")
    start_time_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    approved_sha = os.environ.get("CHESSHEAT_TARGET_LABEL_DERIVATION_APPROVED_SHA")
    if not check_approved_sha(approved_sha):
        print("ERROR: Invalid CHESSHEAT_TARGET_LABEL_DERIVATION_APPROVED_SHA.")
        sys.exit(1)
        
    if hash_file(PROTOCOL_PATH) != EXPECTED_PROTOCOL_SHA:
        print("FAIL PROTOCOL JSON SHA")
        sys.exit(1)
        
    s_raw = hash_file(SOURCE_PATH)
    t_raw = hash_file(TARGET_PATH)
    seal_path = "artifacts/research/cp_target_acquisition_2026_07/cp_target_acquisition_seal_v2.json"
    seal_raw = hash_file(seal_path)
    
    if s_raw != EXPECTED_SOURCE_SHA:
        print(f"FAIL SOURCE raw SHA: expected {EXPECTED_SOURCE_SHA}, got {s_raw}")
        sys.exit(1)
    if t_raw != EXPECTED_TARGET_SHA:
        print(f"FAIL TARGET raw SHA: expected {EXPECTED_TARGET_SHA}, got {t_raw}")
        sys.exit(1)
    if seal_raw != EXPECTED_TARGET_SEAL_SHA:
        print(f"FAIL TARGET seal V2 SHA: expected {EXPECTED_TARGET_SEAL_SHA}, got {seal_raw}")
        sys.exit(1)
        
    m_raw, total_recs, admitted_recs = hash_manifest(MANIFEST_PATH)
    if m_raw != EXPECTED_MANIFEST_SHA:
        print(f"FAIL manifest SHA: expected {EXPECTED_MANIFEST_SHA}, got {m_raw}")
        sys.exit(1)
    if total_recs != 40038 or admitted_recs != 33859:
        print("FAIL manifest counts")
        sys.exit(1)
        
    os.makedirs(os.path.dirname(OUTPUT_COMPRESSED_PATH), exist_ok=True)
    if os.path.exists(OUTPUT_COMPRESSED_PATH):
        raise FileExistsError(f"Compressed output already exists: {OUTPUT_COMPRESSED_PATH}")
    if os.path.exists(OUTPUT_UNCOMPRESSED_PATH):
        raise FileExistsError(f"Uncompressed output already exists: {OUTPUT_UNCOMPRESSED_PATH}")
        
    print("Executing TargetLabelMaterializerV6 for V7_REPLICATION_1...")
    mat = TargetLabelMaterializerV6(
        manifest_path=MANIFEST_PATH,
        source_path=SOURCE_PATH,
        target_path=TARGET_PATH,
        output_path=OUTPUT_COMPRESSED_PATH,
        manifest_sha=m_raw,
        source_sha=s_raw,
        target_sha=t_raw,
        target_seal_sha=seal_raw,
        approved_sha=approved_sha,
        expectations=FROZEN_JULY_2026_LABEL_EXPECTATIONS
    )
    
    uncompressed_sha = mat.run()
    compressed_sha = hash_file(OUTPUT_COMPRESSED_PATH)
    compressed_bytes = os.path.getsize(OUTPUT_COMPRESSED_PATH)
    print("Compressed materialization complete.")
    print(f"Compressed bytes: {compressed_bytes}")
    print(f"Compressed SHA256: {compressed_sha}")
    print(f"Computed uncompressed SHA256: {uncompressed_sha}")
    
    print("\nDecompressing execution cache for downstream production...")
    dctx = zstd.ZstdDecompressor()
    decompress_sha = hashlib.sha256()
    decompressed_bytes = 0
    tmp_uncompressed = OUTPUT_UNCOMPRESSED_PATH + ".tmp"
    with open(OUTPUT_COMPRESSED_PATH, "rb") as fin, open(tmp_uncompressed, "wb") as fout:
        with dctx.stream_reader(fin) as reader:
            while True:
                chunk = reader.read(65536)
                if not chunk:
                    break
                fout.write(chunk)
                decompress_sha.update(chunk)
                decompressed_bytes += len(chunk)
                
    actual_decomp_sha = decompress_sha.hexdigest()
    if actual_decomp_sha != uncompressed_sha:
        raise ValueError(f"Decompression stream SHA mismatch: {actual_decomp_sha} != {uncompressed_sha}")
        
    os.rename(tmp_uncompressed, OUTPUT_UNCOMPRESSED_PATH)
    print("Execution cache materialized successfully.")
    print(f"Decompressed bytes: {decompressed_bytes}")
    print(f"Decompressed SHA256: {actual_decomp_sha}")
    
    end_time_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Construct seal
    seal = {
        "schema": "CP_TARGET_LABEL_DERIVATION_SEAL_V7_REP1",
        "status": "TARGET_LABEL_DERIVATION_V7_REP1_SEALED",
        "label_derivation_protocol": "CP_TARGET_LABEL_DERIVATION_V7_REPLICATION_1",
        "authorization_scope": "LABEL_MATERIALIZATION_AND_EVIDENCE_SEALING_ONLY",
        "protocol_id": "CP_REPRESENTATION_EFFICIENCY_PROTOCOL_V7",
        "protocol_json_sha256": EXPECTED_PROTOCOL_SHA,
        "implementation_sha": approved_sha,
        "manifest_decompressed_sha256": EXPECTED_MANIFEST_SHA,
        "source_raw_sha256": s_raw,
        "target_raw_sha256": t_raw,
        "target_acquisition_seal_v2_sha256": seal_raw,
        "root_record_count": 33859,
        "pair_eligible_root_count": 33444,
        "zero_pair_root_count": 415,
        "source_pair_count": 17788903,
        "all_partition_counts": {"TRAIN": 23639, "VALIDATION": 5148, "TEST": 5072},
        "eligible_partition_counts": {"TRAIN": 23350, "VALIDATION": 5094, "TEST": 5000},
        "compressed_artifact_identity": "TRANSPORT_ONLY",
        "compressed_bytes": compressed_bytes,
        "compressed_sha256": compressed_sha,
        "scientific_artifact_identity": "UNCOMPRESSED_CANONICAL_JSONL_SHA256",
        "decompressed_bytes": decompressed_bytes,
        "decompressed_canonical_sha256": actual_decomp_sha,
        "output_path": OUTPUT_COMPRESSED_PATH,
        "execution_cache_path": OUTPUT_UNCOMPRESSED_PATH,
        "runtime_pin_sha256": hash_file("artifacts/research/target_label_derivation_runtime_pin_v1.json"),
        "runtime_requirements_sha256": hash_file("requirements/target-label-runtime-v1.txt"),
        "execution_start_utc": start_time_utc,
        "execution_end_utc": end_time_utc,
        "execution_count": 1,
        "execution_exit_status": 0,
        "execution_command": f"PYTHONPATH=src:. CHESSHEAT_TARGET_LABEL_DERIVATION_APPROVED_SHA={approved_sha} .venv/bin/python3 -u scripts/run_cp_target_label_derivation_rep1.py",
        "model_training_performed": False,
        "scientific_outcome_analysis_performed": False
    }
    
    with open(SEAL_PATH, "w", encoding="utf-8") as sf:
        json.dump(seal, sf, sort_keys=True, separators=(",", ":"))
        
    print(f"\nSeal successfully created at {SEAL_PATH}")
    print("SUCCESS: V7_REPLICATION_1_LABEL_DERIVATION_COMPLETE")

if __name__ == "__main__":
    main()
