# CP_TARGET_LABEL_DERIVATION_IMPLEMENTATION_V1

This document describes the implementation of the target pair label derivation (V1) for ChessHeat.

## Immutable Boundary
- The frozen protocol JSON `ea1242de3b2f0ac1613ac9b838f014ad00ae8910cfd51d8b99c6fb77f15e29ef` strictly governs label semantics.
- `src/chessheat/attribution.py:compare_scores` and `src/chessheat/models.py:Score` are imported directly to avoid changing frozen label determination logic.

## Expected SHAs for Real Execution
- **Manifest**: `5a013e64265820b65d1d3687fcee98aa607ab41470294d11df7b2f803c8e063d`
- **SOURCE Raw**: `7eb640c572dad4c6607cfb1b5ccf99597672042e5c516f131feab02223ccfa6b`
- **TARGET Raw**: `d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00`
- **TARGET Seal V2**: `1f17ac7e27531d27bc050d49a8a1e60aa5e0ab53c26f28b2540f868c27a43dad`

## Source Pair Eligibility & Orientation
Eligible moves are restricted strictly to SOURCE valid observations with integer `CP` score types. Source `MATE` typed observations are dropped from pair construction, as preregistered.
Moves are ordered lexicographically by UCI to yield canonical pairwise orientations (`m1 < m2`). The pair set is `k choose 2`.

## Target Information Boundary
Target mate properties are preserved *only* to compare mate lengths (which determines `FIRST_BETTER` vs `SECOND_BETTER` vs `EQUAL`), but the magnitude itself (e.g., target CP value, target mate distance) is not returned in the learner dataset.

## Identifiers and Split
- **Pair ID Domain**: `CHESSHEAT_TARGET_PAIR_V1|<root_identity>|<m1_uci>|<m2_uci>`
- **Split**: Bound to `get_partition(sufficient_position)` from `protocol_freeze.py`.

## Source-Known Count Gates
Future execution scripts will independently enforce:
- Declared roots: 33859
- SOURCE zero-pair roots: 415
- TRAIN: 23350, VALIDATION: 5094, TEST: 5000
- SOURCE pair count: 17788903

## Claim Boundary
Zero real-world scientific labels were generated during this implementation. The implementation purely operationalizes the transform of immutable SOURCE and TARGET facts into structural training sets. Real July derivations are NOT YET AUTHORIZED.
