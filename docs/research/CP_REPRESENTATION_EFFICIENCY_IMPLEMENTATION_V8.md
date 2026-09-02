# CP Representation Efficiency Implementation V8

This document records the V8 repair of the downstream training implementation, restoring test compatibility, execution isolation, target-label schema compliance, and authorization boundaries.

## Scope

The repair addressed exactly four execution boundaries:

A. **Schema Compatibility**: Verified real `CP_TARGET_PAIR_LABEL_ROOT_V6` schemas with canonical derivation semantics. Removed the spurious assumption that `side_to_move` was hoisted to the root level. Properly validated integer values, explicit strings, null counts, and strictly increasing string lexical sorting of UCI pairs.
B. **Authorization Gates**: Implemented `verify_approved_sha_gate()` leveraging byte-for-byte local git tree inspection and ancestor checks against tracked files rather than assuming HEAD identity. Strict distinction between `CHESSHEAT_REAL_TRAINING_V1_AUTHORIZED` and `CHESSHEAT_SCIENTIFIC_ANALYSIS_V1_AUTHORIZED`.
C. **Execution Shell**: Correctly implemented the `verify_training_evidence_preflight()`, single-pass `DerivedCache` with offset byte access, population splitting with eight fixed budgets, `build_job_specs()` (160 unique determinism specs), and a true multi-process local runner in `run_job_specs()`.
D. **Runner Entrypoint Integrity**: Modified `scripts/run_cp_representation_efficiency.py` to parse its arguments cleanly before invoking environment state gates.

## Validation

The implementation passed the required positive control using synthetic inputs through the actual `derive_root_pair_labels_v6` generator, fed directly into the newly corrected V8 downstream schema validator.

It also passes the required 13-case hostile SHA matrix, mocking edge cases including detached branch drift, uncommitted changes, and docs-only downstream merges.

## Current Status

**DOWNSTREAM_TRAINING_IMPLEMENTATION_V8_IMPLEMENTED_REAUDIT_REQUIRED**

The V8 code currently omits the complete learner rewrite requested in V4, addressing only the schema, shell, gates, and runner execution to clear the path for isolated reaudit of the core evidence pipelines.

