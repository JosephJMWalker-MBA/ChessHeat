#!/usr/bin/env python3
import os
import sys
import hashlib
import subprocess
from chessheat.cp_target_labels import TargetLabelMaterializerV6, FROZEN_JULY_2026_LABEL_EXPECTATIONS

MANIFEST_PATH = "artifacts/research/cp_source_feasibility_2026_07/cp_root_population_manifest_v2.jsonl.zst"
SOURCE_PATH = "artifacts/research/cp_source_feasibility_2026_07/raw/cp_source_root_results_v2.jsonl"
TARGET_PATH = "artifacts/research/cp_target_acquisition_2026_07/raw/cp_target_root_results_v2.jsonl"
OUTPUT_PATH = "artifacts/research/cp_target_labels_2026_07/cp_target_pair_labels_v6.jsonl.zst"
PROTOCOL_PATH = "artifacts/research/cp_representation_efficiency_protocol_v7.json"

def hash_file(path):
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()
    
def hash_manifest(path):
    import zstandard as zstd
    import json
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
        "src/chessheat/cp_root_population.py",
        "scripts/run_cp_target_label_derivation.py"
    ]
    
    # check uncommitted changes
    diff = subprocess.run(["git", "diff", "--quiet", "HEAD", "--"] + bound_files)
    if diff.returncode != 0:
        return False
        
    # Check staged changes
    diff_staged = subprocess.run(["git", "diff", "--cached", "--quiet", "--"] + bound_files)
    if diff_staged.returncode != 0:
        return False
        
    # Check that HEAD tree matches the SHA tree for those files
    diff2 = subprocess.run(["git", "diff", "--quiet", sha_val, "HEAD", "--"] + bound_files)
    if diff2.returncode != 0:
        return False
        
    return True

def main():
    import zstandard as zstd
    print(f"Using zstandard: {zstd.__version__}")
    
    approved_sha = os.environ.get("CHESSHEAT_TARGET_LABEL_DERIVATION_APPROVED_SHA")
    if not check_approved_sha(approved_sha):
        print("ERROR: Invalid CHESSHEAT_TARGET_LABEL_DERIVATION_APPROVED_SHA.")
        sys.exit(1)
        
    if hash_file(PROTOCOL_PATH) != "ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef":
        print("FAIL PROTOCOL JSON SHA")
        sys.exit(1)
        
    s_raw = hash_file(SOURCE_PATH)
    t_raw = hash_file(TARGET_PATH)
    
    seal_path = "artifacts/research/cp_target_acquisition_2026_07/cp_target_acquisition_seal_v2.json"
    seal_raw = hash_file(seal_path)
    
    if s_raw != "7eb640c572dad4c6607cfb1b5ccf99597672042e5c516f131feab02223ccfa6b":
        print("FAIL SOURCE raw SHA")
        sys.exit(1)
    if t_raw != "d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00":
        print("FAIL TARGET raw SHA")
        sys.exit(1)
    if seal_raw != "1f17ac7e27531d27bc050d49a8a1e60aa5e0ab53c26f28b2540f868c27a43dad":
        print("FAIL TARGET seal V2 SHA")
        sys.exit(1)
        
    m_raw, total_recs, admitted_recs = hash_manifest(MANIFEST_PATH)
    if m_raw != "5a013e64265820b65d1d3687fcee98aa607ab41470294d11df7b2f803c8e063d":
        print("FAIL manifest SHA")
        sys.exit(1)
    if total_recs != 40038 or admitted_recs != 33859:
        print("FAIL manifest counts")
        sys.exit(1)
        
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        
    mat = TargetLabelMaterializerV6(
        manifest_path=MANIFEST_PATH,
        source_path=SOURCE_PATH,
        target_path=TARGET_PATH,
        output_path=OUTPUT_PATH,
        manifest_sha=m_raw,
        source_sha=s_raw,
        target_sha=t_raw,
        target_seal_sha=seal_raw,
        approved_sha=approved_sha,
        expectations=FROZEN_JULY_2026_LABEL_EXPECTATIONS
    )
    
    uncompressed_sha = mat.run()
    print("SUCCESS")
    print(f"Uncompressed canonical SHA256: {uncompressed_sha}")

if __name__ == "__main__":
    main()
