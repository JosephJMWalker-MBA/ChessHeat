# CP_TARGET_LABEL_DERIVATION_IMPLEMENTATION_V3

This document preserves the failed V2 architecture bug and validates the V3 repair.

## V2 Pre-Audit Failure
The V2 implementation failed pre-audit review before hostile validation because:
1. Production data_payload substring matching was incompatible with canonical `ExperimentResult` JSON spacing.
2. Unit tests bypassed the production materializer completely, calling inner functions directly.
3. Output determinism tests replaced the production `run()` with a duplicated `_mocked_run`.
4. The named roundtrip test was effectively a pass/no-op due to missing implementations in tests.
5. Full SOURCE-known partition/count gates were not executable cleanly in synthetic tests.
6. Hostile approved-SHA and malformed-input coverage was incomplete.

## V3 Architecture
V3 explicitly removes ALL duplicate parsing. `ExperimentResult(**outer["experiment_result"])` validates canonical payload serialization exactly in both production and test flows. 

A single parameterized execution flow leverages `_validate_source_success` and `_validate_target_success` acting upon dictionaries, rejecting string-based inference.

Expectations are now encoded in an immutable dataclass `LabelMaterializationExpectations`, preventing tests from rewriting truth but allowing small synthetic overrides without mocking logic.

Roundtrip determinism executes via genuine materializer execution.

## Root of Trust
Execution requires `CHESSHEAT_TARGET_LABEL_DERIVATION_APPROVED_SHA`. Tests formally validate strict equality of all bounds against git representations, verifying unstaged drift, staged drift, invalid SHA domains, and missing refs.

## Real Data Bound
Target data derivation against the real July 2026 dataset remains unauthorized until explicit governance release is generated after the subsequent independent V3 implementation re-audit.

