# TARGET Label Evidence V2 Audit

This document serves as the formal record of the independent, hostile, read-only audit of the real July V6 TARGET label materialization. 

## Context and Identities
- **V6 Implementation SHA:** 14b85055fd439cf7f905adf51718544485b1ac17
- **Materialization Evidence Commit SHA:** 63cb0a2e493e4c1bf6e87f6083912582ed83217d
- **V2 Repair Commit SHA:** 0c2b256510d4cad08206d83b0372310d004b7054

## Seal Verification
- **V1 Seal SHA:** c53efd42bf56cebd8ebde7ed4a7abc6732454e5e77c40d30bde8b67eee11e937
- **V1 Verdict:** TARGET_LABEL_DERIVATION_SEAL_V1_PREAUDIT_FAIL (Missing required `schema` field)
- **V2 Seal SHA:** 2e4735f40124f4eb7017ff816a4ea55e9f72ac559236a6077a0104273b1ab9c4
- **V2 Canonical-Byte Verdict:** PASS. File strictly conforms to canonical serialization semantics without a trailing newline.

## Input Evidence Validation
All cryptographic inputs were independently stream-verified against their real file bytes before and after the audit.
- SOURCE Raw SHA256: 7eb640c572dad4c6607cfb1b5ccf99597672042e5c516f131feab02223ccfa6b (PASS)
- TARGET Raw SHA256: d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00 (PASS)
- TARGET Acquisition Seal V2: 1f17ac7e27531d27bc050d49a8a1e60aa5e0ab53c26f28b2540f868c27a43dad (PASS)
- Protocol V7 JSON: ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef (PASS)
- Manifest Decompressed SHA256: 5a013e64265820b65d1d3687fcee98aa607ab41470294d11df7b2f803c8e063d (PASS)

## Label Artifact Audits
- **Compressed Artifact Identity:** dea9346f9cb125f9c35e8824bb937daf4ea7fc51cff7f6c7c437caac8ae2c92d (913,691,406 bytes) (PASS)
- **Decompressed Scientific Identity:** c54c897b1e1db14ae507a4ea4c23463aaed4a5be23b7d44cf34422a9e3bde4d2 (3,933,405,259 bytes) (PASS)
- **Canonical-Stream Verdict:** PASS. Every root record exactly satisfied canonical JSON sorting, no-nan representation, and precise newline boundaries.
- **Root-Order/Identity Verdict:** PASS. All 33,859 admitted roots exactly match the stream of the independently decompressed manifest, along with expected cross-stream digests and partitions.

## Independent Pair Population
- **Pair Reconstruction:** Reconstructed all SOURCE combinations based on Protocol V7 admission rules directly from genuine unparsed raw SOURCE results, independent of the production label generator.
- **Pairs Checked:** 17,788,903
- **Pair ID Verdict:** PASS. 100% exact match to artifact.
- **SOURCE Feature Verdict:** PASS. 100% exact match (`source_cp_m1`, `source_cp_m2`, `d_X`, `a_X`).
- **Pair-ID Uniqueness Proof:** Global uniqueness is proven by invariance: the manifest ensures global uniqueness of `root_identity`. Within any given root, pairs are constructed strictly from a strictly monotonically sorted (lexical string) universe without replacement (`i < j` iteration). Therefore, every combined `root_identity` + `m1` + `m2` tuple is structurally unique globally.

## Independent TARGET Labeling
- **Target-Label Total Checked:** 17,788,903
- **Target-Label Mismatch Count:** 0
- **TARGET Failure Semantics:** Verified all TARGET-invalid pairs accurately propagate `null` target_label with `TARGET_ACQUISITION_FAILURE` reason without inflating outcome classes.

## Information Boundary Verification
- **Key-Name Inventory:** `['a_X', 'conservative_split_group', 'd_X', 'ep_target_square', 'label_derivation_protocol', 'label_derivation_software_revision', 'm1_uci', 'm2_uci', 'pair_id', 'pairs', 'partition', 'protocol_id', 'protocol_json_sha256', 'root_identity', 'root_record_digest', 'schema', 'source_cp_m1', 'source_cp_m2', 'source_cp_move_count', 'source_pair_count', 'source_raw_sha256', 'source_status', 'sufficient_position', 'target_evaluable_pair_count', 'target_label', 'target_non_evaluable_pair_count', 'target_non_evaluable_reason', 'target_raw_sha256', 'target_seal_v2_sha256', 'target_status']`
- **Information-Boundary Verdict:** PASS. No learner-facing raw CP, mate distances, raw TARGET observations, PV strings, or TARGET magnitudes were leaked into the final representation payload.

## Structural Constraints
- **Roots:** 33,859
- **Pair-Eligible Roots:** 33,444
- **Zero-Pair Roots:** 415
- **SOURCE Pair Count:** 17,788,903
- **Partition Counts (All):** TRAIN: 23639, VALIDATION: 5148, TEST: 5072 (PASS - Exact match from independent protocol recomputation)
- **Partition Counts (Eligible):** TRAIN: 23350, VALIDATION: 5094, TEST: 5000 (PASS)

## Assertions & Limitations
- **Before/After Immutability Verdict:** PASS.
- **Non-Reexecution Confirmation:** PASS. Production was NOT re-invoked. Artifact remains immutable.
- **Execution-Log Limitation:** ORIGINAL_EXECUTION_LOG_NOT_PRESERVED. Recorded as an unavoidable factual limitation because the original standard output trace of the materialization was deleted. 
- **Scientific Label Distribution:** NOT COMPUTED.
- **Scientific Outcome Analysis:** NOT PERFORMED.
- **Model Training:** 0 / UNAUTHORIZED.

## Final Verdict
**TARGET_LABEL_EVIDENCE_V2_AUDIT_PASS**
