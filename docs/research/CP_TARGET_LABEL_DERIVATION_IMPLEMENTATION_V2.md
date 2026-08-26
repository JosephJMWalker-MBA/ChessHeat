# CP_TARGET_LABEL_DERIVATION_IMPLEMENTATION_V2

This document describes the repaired implementation (V2) of the target pair label derivation for ChessHeat.

## Implemented V2 Fixes
- `ExperimentResult` is correctly utilized for both source and target records to seamlessly enforce canonical JSON payload validations and `artifact_digest` checks.
- Real CP observation schemas (`canonical_acquisition_index`, `isolation_sequence_index`, `root_move_uci`) are explicitly enforced against mismatches.
- The catch-all `except` block for `UNORDERED` assignment was entirely dropped. Malformed states appropriately fail-closed and halt derivation.
- `CHESSHEAT_TARGET_LABEL_DERIVATION_APPROVED_SHA` is now robustly checked against Git, verifying uncommitted changes and precisely matching code signatures of all execution-bound files.
- The manifest hash utilizes the valid `5a013e...` hash on the real *decompressed* JSONL payload, avoiding ambiguous compressed-byte SHAs.
- Roundtrip compression tests verify Zstandard determinism and identical `uncompressed_sha256` identity.
- Explicit gate constraints correctly assert that identically 33,859 roots, 415 zero-pair roots, and exactly 17,788,903 output pair results pass cleanly.

## Immutable Boundary
- Protocol JSON `ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef` strictly rules semantic logic.
- Target data preserves ONLY explicit comparisons logic without revealing absolute TARGET CP scores to output.

## External Governance
Target Derivation remains unauthorized until explicit governance releases it, pending independent hostile audit of V2.

