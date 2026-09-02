# Downstream Representation Efficiency Implementation V4

## History
- **V1**: `DOWNSTREAM_TRAINING_IMPLEMENTATION_V1_PREAUDIT_FAIL`
- **V2**: `DOWNSTREAM_TRAINING_IMPLEMENTATION_V2_PREAUDIT_FAIL`
- **V3**: `DOWNSTREAM_TRAINING_IMPLEMENTATION_V3_PREAUDIT_FAIL`
- **V4**: `DOWNSTREAM_TRAINING_IMPLEMENTATION_V4_IMPLEMENTED_REAUDIT_REQUIRED`

*Note: The previous premature V3 `PREAUDIT_PASS` claim in `artifacts/research/V3_REPAIR_REPORT.md` is append-corrected by this governance document. V3 actually failed audit, requiring V4.*

## Changes in V4
- Elimination of all placeholders, `pass`, and empty tests across the training boundaries.
- Unified canonical pair order `(m1_uci < m2_uci)` validation accepting non-monotonic `pair_id` strings.
- Complete V6 Root Schema matching required for synthetic fixtures.
- Real Training Authorization strictly fails-closed before any processing.
- `DerivedCache` deterministically tracks scientific SHA payloads for populations.
- Nominal root budgets enforced across exactly 160 deterministic training iterations (4 conditions, 8 budgets, 5 seeds).
- Target attrition strictly drops non-evaluable training roots without replacement.
- Early Stopping State Machine rigorously tracking `mean(root mean NLL)` improvements.
- Checkpoint / Test Once strictly isolating restore operations.
