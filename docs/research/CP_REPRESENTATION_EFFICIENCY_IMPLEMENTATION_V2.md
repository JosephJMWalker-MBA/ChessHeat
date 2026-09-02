# CP Representation Efficiency Implementation V2

This document describes the V2 repair of the downstream training and analysis implementation for the CP Representation Efficiency experiment.
It honors the objective scientific mechanics exactly as frozen in Protocol V7 and operationalized under ML Runtime V3.

## Frozen V7 Scientific Mechanics
- **Model Topology**: 19x8x8 spatial encoding (Conv64->ReLU->Conv64->ReLU->Conv64->ReLU->GAP) and 270 side info (Linear128->ReLU). Concat -> Linear128 -> ReLU -> Linear3. No dropout, no batch normalization. Total parameters: 144,643.
- **Root Budgets**: Selection strictly nested across 250, 500, 1000, 2000, 4000, 8000, 16000, 20000 roots. Roots with 0 TARGET-evaluable pairs are dropped *after* budget inclusion.
- **Loss Calculation**: Pair-level cross entropy evaluated evenly, then averaged per-root. Optimizer updates exactly once per minibatch of 64 effective roots.
- **Representations**: 
  - `mu_D` uses the destination-only spatial organization (`build_m_d`).
  - `mu_T` uses transition-touch spatial organization (`build_m_t`).
  - `B_daS` uses a mandatory zero-spatial baseline (`build_m_zero`).
  - `B_perm` uses a matched permuted-spatial diagnostic/control (`build_m_perm`). `B_raw` is not executed in V2 pipeline.

## V2 Mechanical Execution Disambiguations
These specific mechanics resolve ambiguity but do **not** change data population, input info, model family, root weighting, training objective, primary contrast, or inference rules:

1. **Epoch Indexing**: Completed training epochs are indexed 0..199, and the first epoch evaluated uses `e=0`.
2. **Early Stopping Bounds**: The non-improvement counter starts at 0 upon discovering a new best NLL, increments after any validation lacking strict improvement (`min_delta = 0.0`), and stops once the counter hits 20. Earliest epoch wins a tie.
3. **No Pair Microbatching**: All valid pairs within a root are forwarded simultaneously in a single PyTorch pass without chunking. The root mean loss is aggregated and scaled analytically (`/ B` roots) to ensure identical objective values while keeping backward graph complexity bounded to one root at a time. The maximum pair count is 23653, which safely fits in MPS/M4 memory.
4. **Canonical State Digest**: PyTorch checkpoint bytes are opaque. Scientific identity is established by iterating over `state_dict()` keys alphabetically and hashing their contiguous Apple Silicon little-endian float32 raw bytes (`t.untyped_storage().tolist()`) along with tensor name, dtype, and shape.
5. **B_RAW Non-Execution**: `B_raw` is not executed in the primary V2 pipeline (`B_RAW_NOT_EXECUTED_IN_PRIMARY_V2_PIPELINE`) as its architecture is not fully specified.

## Execution / Hostile Protections
- Real execution is explicitly prevented behind multiple isolation gates (`CHESSHEAT_DOWNSTREAM_TRAINING_APPROVED_SHA`, `CHESSHEAT_REAL_TRAINING_AUTHORIZED`). 
- Analysis code runs isolated from training code, protected by `CHESSHEAT_SCIENTIFIC_ANALYSIS_AUTHORIZED`.
- `B_perm` is structurally excluded from the `full_bootstrap_procedure` gate to prevent contamination of the analysis.
