# TARGET Label Derivation V6 Re-Audit Supplement 2

This supplement formally invalidates the independent hostile matrix executed in Supplement 1 and substitutes a corrected audit.

**V6 implementation SHA**: 14b85055fd439cf7f905adf51718544485b1ac17
**Initial audit SHA**: fffae6ebb9e2845d1116b6b14bc366f1861cf87b
**Supplement 1 SHA**: e1f7d116eccb997bc2b57c11ec434fdba22f6db9

## Reason for Supplement 2

Supplement 1 hostile-matrix evidence was structurally insufficient: the baseline assigned acquisition indices *before* lexically sorting observations. Thus, the baseline itself was technically malformed (violating index validation gates).

## 1. Audit Protocol Violation: `dictdiffer`
Supplement 1 installed `dictdiffer` without authorization.
- `python -m pip show dictdiffer` -> **Package not found** (Failed network in prior sandbox)
- `_verify_runtime_pin()`: **PASS**
- **Verdict**: The prior installation attempt is an AUDIT_PROTOCOL_VIOLATION, but it remains strictly NONMATERIAL as every V6 pinned runtime identity (including `zstandard` native objects) continues to match exactly.

## 2. Baseline Positive Control
A strictly canonical valid baseline was constructed (observations sorted *before* final index assignments).
- **Result**: `BASELINE_VALID_ACCEPTED = 1`
- `_validate_source_success`: PASS
- `_validate_target_success`: PASS
- `source_cp_move_count` = 2, `source_pair_count` = 1
- **Expected vs Actual Pair ID**: EXACT MATCH (`934c9e98c8d85b69be215e6930d0c0e72d1507f7eaf834b8388eed6964e6db26`).

## 3. Hostile Record Matrix Verification
Against the validated baseline, 44 discrete mutations were applied.
- **Matrix totals**: 44 rejected / 44 total.
- **Expected gate matches**: 44 / 44 exactly matched the precise exception substring intended.
- **Legal-universe isolation verdict**: PASS. Case 43 properly passed internal TARGET integrity checks and correctly bounded out at `SOURCE/TARGET legal-universe mismatch`.
- **Source-failure/Target-validation verdict**: PASS. A valid SOURCE FAILURE combined with an invalid TARGET successfully rejected the invalid TARGET instrument, proving TARGET validation is not short-circuited.

## 4. Semantic Roundtrip Execution
Run directly on `TargetLabelMaterializerV6.run()` with valid `LabelMaterializationExpectations`:
- **Run1 SHA**: `5baa578ae10aa93d3a3f9f87c2b1648ea4e8104189ba6d181f024096ea1e0b76`
- **Run2 SHA**: `5baa578ae10aa93d3a3f9f87c2b1648ea4e8104189ba6d181f024096ea1e0b76`
- `run1 returned SHA == run2 returned SHA`: True
- `decompressed bytes run1 == run2`: True
- `run1 returned == independently decompressed`: True
- `run2 returned == independently decompressed`: True
- **Transport determinism**: compressed bytes equal.
- **Semantic Assertions**: 1 root, 1 pair, correct CP values (5, 10), correct differences (`a_X=5`, `d_X=SOURCE_SECOND_BETTER`, `target_label=SECOND_BETTER`).
- **Pair ID Assertions**: Matches derived SHA256 exactly.

## 5. Information Boundary Adjudication
A recursive structural key sweep over the production roundtrip output yielded:
`TARGET KEYS: ['ep_target_square', 'target_evaluable_pair_count', 'target_label', 'target_non_evaluable_pair_count', 'target_raw_sha256', 'target_seal_v2_sha256', 'target_status']`
- **Verdict**: PASS. No score values, raw metrics, or CP magnitudes leak into the output representation.

## 6. Target-Invariance & CompareTyped
- `CompareTyped`: PASS (14/14 explicit logic conditions mathematical limits).
- `TARGET_INVARIANCE`: True (Scores 100/-100 inverted to -100/100 changed ONLY the derived target label).
- `TARGET_FAILURE_INVARIANCE`: True (Label is NULL, reason is `TARGET_ACQUISITION_FAILURE`).

## 7. Artifact Integrity
- **SOURCE SHA before/after**: `7eb640c572dad4c6607cfb1b5ccf99597672042e5c516f131feab02223ccfa6b`
- **TARGET SHA before/after**: `d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00`
- **Real July V1-V6 absence before/after**: PASS.

## Audit Temporary Scripts
- `148244b3d4b7e827f1ee6d43781ad089b1ba895f2d69aeabc080c6019ece4475  baseline.py`
- `4d184e0c2452ba9513be62d96a0d804afa229774a5f2dce61717971f85395888  hostile3.py`
- `9003ea06e09470eed4fc9722c3fe6f78d378aaa300864d4a7362d978fb3429ca  roundtrip2.py`
- `2235803496986b6bb0b01901db7fd834d4de6002e212b771b616b256c4a0fdfa  compare.py`
- `b2742302c53013c0ab2d9438c98a4ce0df81da15dca1f38b8fdb216a4faa01d7  invariance.py`

## Final Verdict
TARGET_LABEL_DERIVATION_V6_REAUDIT_PASS
