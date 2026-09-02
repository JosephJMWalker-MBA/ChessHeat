# CP Target Label Derivation Execution V6

**Authorization Boundary:** LABEL_MATERIALIZATION_AND_EVIDENCE_SEALING_ONLY
**Implementation SHA:** 14b85055fd439cf7f905adf51718544485b1ac17
**Initial Audit SHA:** fffae6ebb9e2845d1116b6b14bc366f1861cf87b
**Authoritative Supplement 2 SHA:** 8b7ecb1460bfd7073fc299d75afa16c6fd6462d8

## Execution Details
- **Start UTC:** 2026-09-02T00:13:33Z
- **End UTC:** 2026-09-02T00:15:35Z
- **Exact Command:** `PYTHONPATH=src:. CHESSHEAT_TARGET_LABEL_DERIVATION_APPROVED_SHA=14b85055fd439cf7f905adf51718544485b1ac17 .venv/bin/python3 -u scripts/run_cp_target_label_derivation.py`
- **Exit Status:** 0
- **Execution Count:** 1 (No retry occurred)

## Runtime Identities
- **Runtime Pin SHA256:** dc707aa6d2709fcdfb108263356a8b0cab4cc459dffd29ba5524241f48ea3e22
- **Requirements Pin SHA256:** da56c02977e00d88d897af40d227d773822aa7134d30e1d40c68e1518d666026

## Input Hashes (Before & After)
- **SOURCE Raw SHA256:** 7eb640c572dad4c6607cfb1b5ccf99597672042e5c516f131feab02223ccfa6b (Unchanged)
- **TARGET Raw SHA256:** d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00 (Unchanged)
- **Target Seal V2 SHA256:** 1f17ac7e27531d27bc050d49a8a1e60aa5e0ab53c26f28b2540f868c27a43dad (Unchanged)
- **Protocol V7 JSON SHA256:** ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef (Unchanged)
- **Manifest Decompressed SHA256:** 5a013e64265820b65d1d3687fcee98aa607ab41470294d11df7b2f803c8e063d (Unchanged)

## Output Artifact
- **Path:** artifacts/research/cp_target_labels_2026_07/cp_target_pair_labels_v6.jsonl.zst
- **Compressed SHA256:** dea9346f9cb125f9c35e8824bb937daf4ea7fc51cff7f6c7c437caac8ae2c92d
- **Compressed Bytes:** 913691406
- **Decompressed Canonical SHA256:** c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2
- **Decompressed Bytes:** 3933405259

## Frozen Structural Counts
- **Total Roots:** 33859
- **Pair-Eligible Roots:** 33444
- **Zero-Pair Roots:** 415
- **Source Pairs:** 17788903
- **All Partition Counts:** TRAIN 23639, VALIDATION 5148, TEST 5072
- **Eligible Partition Counts:** TRAIN 23350, VALIDATION 5094, TEST 5000

## Evidence Seal
- **Path:** artifacts/research/cp_target_labels_2026_07/cp_target_label_derivation_seal_v1.json
- **Seal SHA256:** c53efd42bf56cebd8ebde7ed4a7abc6732454e5e77c40d30bde8b67eee11e937

## Limitations & Assertions
- No label distributions were calculated.
- No scientific outcome analysis occurred.
- Training count = 0.
