# TARGET Label Derivation Re-Audit V6

**Audited SHA**: 14b85055fd439cf7f905adf51718544485b1ac17
**Lineage**: 14b85055fd439cf7f905adf51718544485b1ac17 is exactly one commit ahead of e1cb430f9272c32ffe16bebdf1458a16dce891f3.
**Changed File Scope**: Limited to expected V6 repair surface (pin, docs, run_cp_target_label_derivation.py, cp_target_labels.py, test_cp_target_labels.py). No scientific semantic drift observed.
**Runtime Pin SHA**: dc707aa6d2709fcdfb108263356a8b0cab4cc459dffd29ba5524241f48ea3e22
**Requirements SHA**: da56c02977e00d88d897af40d227d773822aa7134d30e1d40c68e1518d666026
**Actual Runtime Identities**: Python 3.13.5 (542c879fdc2cfe0be223e4729082bac529780d90c6d811c853de852765b35a35), zstandard 0.25.0, extensions MATCH. (PASS)
**Approved-SHA Hostile Results**: ALL PASS (rejects missing, short, blob, tree, staged drift, unstaged drift, runtime-pin drift, runtime-requirements drift, accepts clean HEAD).
**Runtime-Pin Hostile Results**: ALL PASS (rejects wrong schema, python version, zstd version, missing/wrong extensions, mutated compressor config).
**Frozen-Expectation Verdict**: PASS. Actual exception type on mutation: `FrozenInstanceError`.
**Schema/Validator Results**: PASS. Exact adherence to V6 target output identity, strict readback termination (`b""`).
**CompareTyped Result**: PASS. `compare_scores` truth table covers all mate and CP combinations.
**Target Invariance**: PASS. SOURCE identities unmodified during TARGET variations or failures.
**Information Boundary**: PASS. Only target_label/evaluability fields available. No internal values leak.
**Manifest Verification**: PASS. Exact decompressed stream SHA (5a013e64265820b65d1d3687fcee98aa607ab41470294d11df7b2f803c8e063d) and counts verified.
**Raw Evidence SHA Checks**: PASS. SOURCE, TARGET, Protocol, Seal V2 match exact known hashes.
**Completion-Gate Review**: PASS. Output writes atomic. Readback decompressed matching exact counts and bytes.
**Production Roundtrip**: PASS. Exact return matching recomputed SHA on multiple synthetic passes.
**Hostile Record Matrix**: PASS. Reject matrix covers all schema failures.
**Test Counts**: tests/test_cp_target_labels.py (9 passed), tests/test_protocol_freeze.py (36 passed), tests/test_ml_runtime.py (14 passed), full suite (all 287 tests passed).
**Non-Material Warnings**: Frozen dataclass mutation raises `FrozenInstanceError` rather than `TypeError`, but immutability is strictly enforced.
**Real-Label Absence Before/After**: PASS. No real V1-V6 labels found. 0 generated.
**SOURCE/TARGET Immutability**: PASS. Input SHAs identical before and after.

## Final Verdict
TARGET_LABEL_DERIVATION_V6_REAUDIT_PASS
