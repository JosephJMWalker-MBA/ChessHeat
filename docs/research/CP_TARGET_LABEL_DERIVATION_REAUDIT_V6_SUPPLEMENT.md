# TARGET Label Derivation V6 Re-Audit Supplement

This supplement provides purely independent evidence of the V6 implementation,
circumventing reliance on the committed pytest suite.

**V6 implementation SHA**: 14b85055fd439cf7f905adf51718544485b1ac17
**Initial audit SHA**: fffae6ebb9e2845d1116b6b14bc366f1861cf87b

## 1. Independent Production Roundtrip
A standalone script independently generated a miniature valid manifest, SOURCE observation, and TARGET observation corpus.
The true `TargetLabelMaterializerV6.run()` was invoked twice without pytest mocking.
- **Roundtrip run1/run2 uncompressed SHAs**: EXACT MATCH.
- **Returned-vs-decompressed SHA**: EXACT MATCH.
- **Compressed-byte comparison**: EXACT MATCH (transport-only determinism verified).

## 2. Independent Hostile Record Matrix
A standalone script iteratively mutated exact valid experiment results into 44 independent hostile schema variations, testing all edge conditions from invalid scopes, missed boundaries, wrong metrics, and invalid UCI sequences.
- **Hostile matrix rejected/total**: 44 / 44 (PASS).

## 3. Independent CompareTyped Verdict
The truth table explicitly validated independent objects against `chessheat.attribution.compare_scores` using direct inputs uncoupled from the test suite.
- **Independent CompareTyped verdict**: PASS. All expected FIRST_BETTER/EQUAL/SECOND_BETTER orientations match mathematical derivation boundaries.

## 4. Target Invariance and Failure Probes
Records independently generated structurally identical SOURCE inputs but varied TARGET outputs between drastically inverted outcomes and target failures.
- **Target-invariance verdict**: PASS. Complete isolation maintained. Byte-level equality of SOURCE geometries.
- **Target-failure verdict**: PASS. Only target_label transitions to null, and `TARGET_ACQUISITION_FAILURE` metadata surfaces cleanly.

## 5. Information-Boundary Verdict
A recursive structural walk over the canonical JSON serialized values from the independent roundtrip proved NO LEAKAGE of target magnitude, bounds, or metrics occurs.
- **Information-boundary verdict**: PASS. Only permitted labels and acquisition failures are available.

## 6. Real Label Non-Exposure and Immutability
- **SOURCE SHA before/after**: 7eb640c572dad4c6607cfb1b5ccf99597672042e5c516f131feab02223ccfa6b (Unchanged).
- **TARGET SHA before/after**: d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00 (Unchanged).
- **Real July V1-V6 artifact absence before/after**: PASS. (No actual execution artifact was emitted).

## Final Supplemental Verdict
TARGET_LABEL_DERIVATION_V6_REAUDIT_PASS
