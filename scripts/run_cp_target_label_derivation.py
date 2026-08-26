#!/usr/bin/env python3
import os
import sys
import hashlib
from chessheat.cp_target_labels import TargetLabelMaterializerV1

MANIFEST_PATH = "artifacts/research/cp_source_feasibility_2026_07/cp_root_population_manifest_v2.jsonl.zst"
SOURCE_PATH = "artifacts/research/cp_source_feasibility_2026_07/raw/cp_source_root_results_v2.jsonl"
TARGET_PATH = "artifacts/research/cp_target_acquisition_2026_07/raw/cp_target_root_results_v2.jsonl"
OUTPUT_PATH = "artifacts/research/cp_target_labels_2026_07/cp_target_pair_labels_v1.jsonl.zst"

def hash_file(path):
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()

def main():
    if not os.environ.get("CHESSHEAT_TARGET_LABEL_DERIVATION_APPROVED_SHA"):
        print("ERROR: CHESSHEAT_TARGET_LABEL_DERIVATION_APPROVED_SHA environment variable must be set.")
        sys.exit(1)
        
    s_raw = hash_file(SOURCE_PATH)
    t_raw = hash_file(TARGET_PATH)
    m_raw = hash_file(MANIFEST_PATH)
    
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
    if m_raw != "5a013e64265820b65d1d3687fcee98aa607ab41470294d11df7b2f803c8e063d":
        print("FAIL manifest SHA")
        sys.exit(1)
        
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        
    mat = TargetLabelMaterializerV1(
        MANIFEST_PATH,
        SOURCE_PATH,
        TARGET_PATH,
        OUTPUT_PATH,
        m_raw,
        s_raw,
        t_raw,
        seal_raw
    )
    
    # Do not execute in tests. The runner must not proceed if not requested.
    print("Preflight complete.")

if __name__ == "__main__":
    main()
