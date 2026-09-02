# ChessHeat Research Continuity Checkpoint — 2026-08-16

## Purpose

This document is a restart/handoff checkpoint for the ChessHeat research program. It consolidates the current research track, progress report, earned and rejected claims, current preregistration state, implementation constraints, and future-work dependency order.

It is intentionally broader than `NEXT_WORK_MAP.md` and newer than the historical `RESEARCH_REPORT_M1_M8.md`.

The governing rule remains:

> **The mathematics needs to earn the color.**

The central scientific question remains:

> **Which squares or spatial structures matter most to what happens next in a chess position?**

That question has now been decomposed into three separate objects that must not be silently fused:

1. **Shape** — where consequence-related structure is spatially organized.
2. **Amplitude** — how much decision leverage/consequence is present.
3. **Human navigability** — how difficult the structure is for a bounded human to reason through.

Only the first two belong to objective Heat; human navigability remains downstream and separate.

---

# 1. Current Repository Frontier

Latest committed scientific state:

```text
af9d5770d1da139054734983dea0ab6ffa1e986a
Audit CP-only preregistration blockers
```

Current repository documentation/orientation frontier:

```text
f4b8679f0d0cabdff550c1d8d808002743a51319
Remove obsolete Gemini-specific instructions
```

The repository identity is `JosephJMWalker-MBA/ChessHeat`. `README.md` and `AGENTS.md` serve as current orientation surfaces.

The active experiment document is:

```text
docs/research/CP_ONLY_REPRESENTATION_EFFICIENCY_PREREGISTRATION.md
```

Its status is deliberately:

```text
PREREGISTRATION_DRAFT_ONLY
ENGINE_EXECUTION_NOT_AUTHORIZED
MODEL_TRAINING_NOT_AUTHORIZED
```

The CP-only preregistration blocker audit has been **COMPLETED**. Outcome semantics have been repaired (preserving the strict rule that NON-SIGNIFICANCE != EQUIVALENCE), and deterministic outcome classes are now properly defined.

---

# 2. High-Level Progress Report

ChessHeat has moved substantially beyond the original concept of painting engine-derived importance onto 64 squares.

The strongest progress is methodological rather than visual:

- sufficient chess state has been formalized;
- evidence and visualization have been separated;
- branch identity has been preserved where consequence comparisons require it;
- exact provenance and deterministic artifact identities have been added;
- several attractive representation hypotheses have been tested and rejected;
- intervention sensitivity has been distinguished from causal identification;
- objective square ownership has been shown to be non-identified under the current axioms;
- consequence magnitude has been separated from spatial support and source orientation;
- the current valid experimental question has narrowed from “where consequence really lives” to a much more defensible learner-relative representation-efficiency question.

The project is therefore scientifically stronger even though several headline ideas have been falsified or blocked.

The main current result is not a finished Heat scalar. It is a much cleaner statement of what can and cannot yet be claimed.

---

# 3. Research Track — Completed and Frozen Foundations

## M0–M4 — Product and measurement foundation

Completed earlier milestones established:

- concept lock;
- reproducible engine harness;
- direct square-attribution baseline;
- viewer;
- paired-position / geometry-delta primitive.

These remain useful implementation foundations but do not by themselves identify objective square consequence.

## M5–M7 — Falsification and descriptive geometry

These phases established that the project must distinguish descriptive chess geometry from consequence claims.

Important lesson:

> A rule-exact or visually intuitive chess relation is not automatically a privileged measurement basis for consequence.

## M8 — Pivotality

M8 is **frozen**.

The attempted composite pivotality family did not earn universal superiority over its strongest component.

Durable M8 findings include:

- fixed fusion did not universally beat the strongest individual channel;
- rank normalization can manufacture hotspots in low-amplitude positions;
- where leverage is located is not the same quantity as how much leverage exists;
- severity is not decision leverage;
- recurrence depends on the candidate/future set;
- top-5 specificity improved some behavior but reduced hostile-corpus coverage;
- residual non-target Bundle-heavy geography remained;
- `top_n=5` is a development choice, not a discovered law.

Do not retune `ShapeSelectivity-v1` or use the W development corpus to derive a supposedly untouched v2.

---

# 4. S0/S1 — Semantic and Experimental Spine

## S0 — Semantic Freeze v1

Status:

```text
COMPLETE / FROZEN
```

Normative document:

```text
docs/research/SEMANTIC_CONTRACT_V1.md
```

Canonical semantic-signature digest:

```text
5fa4d57cf43c673fa31874ce5d19e777acf0ea695fd032412b193c2123461080
```

Final S0 commit:

```text
0fbcc159c4e4acf0792075007df942742f49a610
```

Important frozen sufficient-state fields:

```text
board_arrangement_fen
side_to_move
castling_rights
en_passant_square
halfmove_clock
fullmove_number
history_available
history_identity
variant
```

Do not silently reduce sufficient state to piece placement alone.

## S1 — Reproducible Experiment Spine

Status:

```text
COMPLETE
```

Identity hardening commit:

```text
9aa91ba94e088a1cccd10313cf255552ae3a669d
```

Key primitives:

```text
SuiteManifest
ExperimentSpec
ExperimentResult
ComparisonResult
```

`ExperimentSpec` v2 binds explicit comparison perspective and must be used for future consequence-comparison experiments.

Historical T3a-2 spec digest:

```text
e2a56fe3da7d965d1bc6080f7028504da9832a0030e5038eff7cdc35d8fa4730
```

S1 remains the provenance spine. Do not create parallel experiment metadata systems for the CP-only work.

---

# 5. T2 Representation Research

## T2b-1

Status:

```text
FALSIFIED
```

A ray transition was reproducible by constituent-square evidence.

## T2b-2

Status:

```text
WEAK_SUPPORT
```

A relation broke a weaker local-square alias, but context-aware square/state representation restored parity / exact reconstruction.

## T2b-3

Status:

```text
FALSIFIED
```

Canonical square-native geometry matched the relation at the audited information boundary.

### Earned T2 conclusion

> Rule-exact relational concepts remain legitimate descriptive coordinates, but the tested ray/blocker family did not earn privileged or irreducible measurement status over a sufficiently capable square/state representation.

Broad graph/relation rescue remains parked.

---

# 6. T3a — Branch-Conditioned Consequence Association

T3a is closed.

Aggregate status:

```text
T3a-1 INCONCLUSIVE
T3a-2 SUPPORTED (single preregistered mechanism-stress fixture)
T3a-3 INCONCLUSIVE
T3a-4 INCONCLUSIVE on provenance / conditional numeric FALSIFIED
```

Important distinction:

```text
LEGAL OPPORTUNITY != SEARCH REALIZATION != CONSEQUENCE
```

Durable conclusion:

> Search realization `E_i(x; J, theta)` earned producer-conditioned observational status, not status as a monotonic primitive of objective consequence.

No fixture hunting, legal-opportunity substitution, MultiPV rescue, or T3a-5 should be introduced simply to obtain a favorable result.

---

# 7. T3b — Legal Reply Intervention

T3b final status:

```text
COMPLETE / CLOSED / FALSIFIED
```

Broad Design-A class contrast:

```text
WEAK_SUPPORT / INTERVENTION_SENSITIVITY
```

Strict matched Design-B result:

```text
FALSIFIED / INTERVENTION_SENSITIVITY
```

Key T3b-9 result:

```text
K = 15 / 16 evaluable
K_min = 12
Q_suite = 5/13
H_0.75 = 2
H_required = 12
classification = FALSIFIED
```

Corrected artifact SHA:

```text
b550f0a5f56a011e66b8e6efdcf50c786453e115b9990b4f1ca4247a521c17db
```

Final closeout commit:

```text
bff498c1145a711dff1290d122b12f8f415228cf
```

Scientific reading:

> Under the frozen Stockfish-18 instrument and independently generated Design-B corpus, rule-selected two-reply destination events were not unusually consequence-sensitive relative to exact same-origin, same-move-form legal alternatives under the preregistered matched calibration.

This does not falsify destination squares in general, square consequence in general, relational geometry, or objective causal effects. It does block promotion of this tested matched destination-specific intervention claim into objective Heat.

---

# 8. Evidence-Tree and Spatial-Ownership Results

## Evidence-tree synthesis

Current synthesis conclusion:

```text
REPRESENTATION_AUDIT_NOT_YET_EARNED
```

Representation gates R0–R2 are representation questions. R3–R5 require a scientifically earned consequence target.

## Spatial Consequence Object Preflight

Status:

```text
COMPLETE / CLOSED
```

Earned result:

```text
SPATIAL_ATTRIBUTION_NOT_IDENTIFIED_BY_CURRENT_AXIOMS
```

Primary conclusion:

```text
SPATIAL_CONSEQUENCE_OBJECT_REQUIRES_EXPLICIT_ATTRIBUTION_AXIOMS
```

The non-identifiability construction showed that multiple square allocations can satisfy the adopted operator constraints for the same supplied abstract consequence mass.

## Spatial Attribution Axiom Preflight

Status:

```text
COMPLETE / CLOSED
```

Earned conclusion:

```text
SPATIAL_OWNERSHIP_IS_CONVENTIONAL_NOT_IDENTIFIED
```

Critical distinction:

```text
empirical utility of mu != truth of ownership semantics
```

An attribution convention can earn predictive, robustness, or intervention utility without becoming discovered spatial ground truth.

---

# 9. Attribution Utility and Source–Target Track

## Attribution Validation Target Preflight

Closed conclusion:

```text
VALIDATION_COMPARISON_REQUIRES_UTILITY_SEMANTICS_FIRST
```

Leading target family:

> held-out legal-alternative consequence discrimination.

## Attribution Utility Semantics Preflight

Closed conclusion:

```text
UTILITY_TASK_REQUIRES_SOURCE_TARGET_BOUNDARY
```

Important distinction:

```text
information gain != representation utility
```

A deterministic spatial bottleneck cannot create information absent from raw source evidence, but it may change accessibility to a constrained learner.

## Attribution Source–Target Boundary Preflight

Closed results:

```text
SOURCE_ATTRIBUTION_MAGNITUDE_NOT_IDENTIFIED
SOURCE_ORIENTATION_SEPARATE_FROM_UNSIGNED_SPATIAL_MASS
CONDITIONAL_INFORMATION_EQUIVALENCE_GIVEN_MOVE_IDENTITY
OPERATIONAL_READOUT_EQUIVALENCE_NOT_YET_IDENTIFIED
```

The key decomposition is:

```text
d_X = ordered source orientation

a_X = unsigned source-score magnitude

G_mu = spatial support / geometry convention

M_mu = a_X * G_mu
```

These are different scientific objects.

A universal cross-typed CP/mate/WDL scalar amplitude is **not earned**.

However:

```text
a_X = 1
```

is admissible for geometry/support experiments only, and:

```text
a_X^CP = |Delta CP_X|
```

is admissible as an instrument-conditioned, task-local CP-only source-score magnitude for CP/CP cases.

It is not objective consequence amplitude and must never be called universal Heat amplitude.

---

# 10. CP-Only Utility Track

## CP-Only Attribution Utility Protocol Feasibility Preflight

Closed conclusion:

```text
CP_ONLY_UTILITY_REQUIRES_READOUT_BOUNDARY
```

A privileged scientific reference move was found to be unnecessary.

Preferred prediction unit:

```text
u = (P, {m, n})
```

for an unordered legal-alternative pair.

Canonical serialization exists only to orient labels reproducibly.

Root-level train/tune/test separation is mandatory because multiple pairs from the same root are statistically dependent.

## CP-Only Readout Boundary Preflight

Closed conclusion:

```text
CURRENT_OPERATORS_ONLY_SUPPORT_CONSTRAINED_EFFICIENCY_TEST
```

Meaning:

> The strongest currently earned information-equalized comparison between the frozen destination-only and transition-touch operators is a learner/resource-constrained efficiency test.

This does not prohibit separately scoped representation-as-delivered studies.

The preferred first estimand is:

```text
information-equalized organization
```

rather than representation-as-delivered, because a raw transition-touch win could simply reflect its already-known preservation of origin information.

Primary utility notion:

```text
sample efficiency
```

This operationalizes learner-relative representation efficiency under a frozen training procedure. It is not a direct observation of intrinsic or universal inductive bias.

---

# 11. Current Preregistration Draft

Document:

```text
docs/research/CP_ONLY_REPRESENTATION_EFFICIENCY_PREREGISTRATION.md
```

Primary question:

> Under one frozen learner/training regime and equalized underlying move information, does destination-only spatial organization or transition-touch organization yield greater sample efficiency for predicting held-out target-instrument ordering of CP/CP-source legal-alternative pairs?

Frozen pieces already include:

- unordered-pair prediction unit;
- canonical UCI lexicographic serialization;
- CP-only source eligibility;
- explicit source orientation `d_X`;
- explicit source magnitude `a_X`;
- destination-only and transition-touch mass operators;
- common model interface;
- `a_X` supplied explicitly to every spatial condition;
- root as the statistical sampling unit;
- all source-eligible pairs used within selected roots;
- multiclass negative log likelihood;
- root-weighted held-out utility;
- normalized trapezoidal AULC on linear training-root count;
- primary operator and baseline contrasts;
- protocol-invalidity conditions;
- raw source treated as information-rich reference, not an empirical performance ceiling.

Current execution blockers:

```text
ROOT_POPULATION_NOT_YET_FROZEN
INSTRUMENT_CONFIG_NOT_YET_FROZEN
P_REPRESENTATION_NOT_YET_FROZEN
LEARNER_FAMILY_NOT_YET_FROZEN
MATCHED_COMPARATOR_NOT_YET_FROZEN
SPLIT_AND_BUDGET_NOT_YET_FROZEN
SEED_SET_NOT_YET_FROZEN
CONFIDENCE_LEVEL_NOT_YET_FROZEN
```

No experiment is authorized while these remain unresolved.

---

# 12. Completed Statistical Repair

The CP-Only preregistration blocker audit was successfully completed. 
The current outcome-class logic avoids treating failure to resolve a difference as evidence of equivalence.

Key repairs already present in the active preregistration:

- `SPATIAL_EFFICIENCY_NO_OPERATOR_PREFERENCE` was replaced with `SPATIAL_EFFICIENCY_OPERATOR_UNRESOLVED`.
- For an uncertainty interval on a contrast Delta with zero superiority boundary:
  ```text
  resolved positive: lower bound > 0
  resolved non-positive: upper bound <= 0
  unresolved: interval contains 0
  ```
- `NO_SPATIAL_EFFICIENCY_ADVANTAGE` strictly requires resolved non-positive evidence for both spatial-vs-baseline contrasts.
- Learning-curve crossings are treated as diagnostics when AULC is the primary estimand; they are not automatically protocol falsifiers.
- Training-seed instability is treated as a diagnostic until a frozen seed-aggregation/inference rule exists.

---

# 13. Existing Implementation Surface Relevant to the Preregistration

## Engine capabilities already present

Current engine code supports:

```text
fixed nodes
fixed depth
fixed time
explicit comparison perspective
Threads configuration
Hash configuration
per-legal-move child-position evaluation
```

The validation harness already evaluates all legal root moves by pushing each move and analyzing the resulting child position.

## Important engine-state gap

Existing all-legal-move acquisition reuses one persistent engine process across move evaluations.

There is currently no explicitly frozen move-level transposition-table/hash-reset boundary.

Therefore the future acquisition protocol must resolve:

```text
ENGINE_STATE_ISOLATION_NOT_YET_IMPLEMENTED
```

before independent source/target observations can be claimed under the new protocol.

The candidate budget type should likely be fixed nodes because the existing harness directly supports node limits, but exact source and target budgets remain to be scientifically justified and frozen.

## Sufficient state

The semantic identity of `P` is already constrained by S0 through `SufficientPosition`.

The remaining blocker is primarily the **numeric learner encoding** of that sufficient state, not its semantic field list.

Useful split:

```text
P_SEMANTIC_IDENTITY_FROZEN_TO_S0
P_NUMERIC_ENCODING_NOT_YET_FROZEN
```

## Machine-learning dependency state

Current `pyproject.toml` includes:

```text
chess
pydantic
pytest (dev)
```

There is no ML framework dependency currently present.

Therefore learner selection is both a scientific protocol choice and a future implementation/dependency decision.

---

# 14. Future Work — Dependency Order
 
 The current work should proceed slowly and in dependency order rather than resolving every open parameter at once.
 
 ## Blocker dependency order
 
 ```text
 1. ROOT_POPULATION_FROZEN_TO_LICHESS_JULY_2026
 2. INSTRUMENT_CONFIG_NOT_YET_FROZEN
    + ENGINE_STATE_ISOLATION_NOT_YET_IMPLEMENTED
 3. source-only feasibility / coverage acquisition
 4. SPLIT_AND_BUDGET_NOT_YET_FROZEN
 5. P_NUMERIC_ENCODING_NOT_YET_FROZEN
 6. LEARNER_FAMILY_NOT_YET_FROZEN
 7. MATCHED_COMPARATOR_NOT_YET_FROZEN
 8. SEED_SET_NOT_YET_FROZEN
 9. CONFIDENCE_LEVEL_NOT_YET_FROZEN
 ```
 
 The first unresolved scientific dependency is now `INSTRUMENT_CONFIG_NOT_YET_FROZEN`.

## First genuinely new implementation work

After the root-population and source-instrument contracts are frozen, the first meaningful code change should be an acquisition path that:

- guarantees declared engine-state isolation;
- acquires all legal-alternative source observations under the frozen source budget;
- produces source-only feasibility/coverage evidence;
- does not acquire or inspect held-out target labels;
- binds results through existing S1 provenance semantics.

Source-only feasibility may measure:

```text
base-root count
legal-move counts
CP-eligible move counts
CP-pair counts
source attrition
execution cost
```

It may not be used to tune against target behavior.

## After source-only feasibility

Only then freeze:

- deterministic root split;
- nested training-root budget schedule;
- numeric encoding of `P`;
- learner family and exact training procedure;
- one matched comparator;
- seed set;
- bootstrap confidence level / uncertainty rule;
- deterministic outcome classifications.

Then conduct an independent preregistration-vs-implementation audit.

Only after that audit should engine execution and model training be separately authorized.

---

# 15. Parked Work

The following remain intentionally parked:

## Representation Audit

```text
PARKED P2 / NOT YET EARNED
```

Do not confuse decodability with causal use or Heat utility.

## Projection Audit

```text
PARKED P2 / GATED
```

A 64-square projection must earn faithfulness relative to a scientifically earned source object.

## T1.12 / Multi-Instrument Robustness

```text
P2 / NO EXECUTION YET
```

Potential future instruments include Stockfish, LC0, and tablebase-grounded cases where appropriate, but robustness must not be used to rescue failed earlier hypotheses.

## Pathways / Evidence Fusion / Amplitude

```text
P3
```

Amplitude remains a separate research problem. Do not assume it is the norm or sum of spatial evidence.

## Human Navigation / Teaching / Explanation

```text
DEFERRED
```

Keep bounded-human decision complexity outside objective Heat.

---

# 16. Research Constraints That Must Survive a Chat Restart

- No new universal Heat scalar merely for convenience.
- No CP/mate fake scalarization.
- No M8 or ShapeSelectivity retuning around falsified results.
- No broad relation/graph architecture rescue without new independent evidence.
- No causal language beyond earned evidence level.
- T3b intervention sensitivity is not causal identification.
- Search realization is not objective consequence.
- Legal opportunity is not search realization.
- Spatial ownership remains conventional / non-identified under the current axioms.
- Attribution utility does not prove ownership truth.
- Producer preference is not consequence.
- Raw evidence is an information-rich reference, not a finite-resource performance ceiling.
- A deterministic spatial representation cannot create information absent from its source, but it may make information easier or harder for a constrained learner to use.
- Source orientation `d_X`, source magnitude `a_X`, and spatial support `G_mu` are separate objects.
- Destination-only and transition-touch maps are conditionally interconvertible when sufficient move identity is supplied.
- Root is the statistical sampling unit for the CP-only efficiency study.
- Negative, falsified, inconclusive, and null results are preserved; do not tune around them.
- No engine/model execution until the preregistration is actually frozen.

---

# 17. Restart Checklist for the Next Chat

A future session should begin by inspecting the repository HEAD.
 
 V3 RE-AUDIT VERDICT: PASS
 
The immediate next task is resolving the first scientific dependency: `EXECUTE_CORRECTED_SOURCE_ONLY_50K_ACQUISITION`.

Then:

1. confirm `NEXT_WORK_MAP.md` agrees with the current preregistration state;
2. inspect `CP_ONLY_REPRESENTATION_EFFICIENCY_PREREGISTRATION.md` for the outcome-semantics repair;
3. verify whether root population and instrument contracts have been frozen;
4. verify whether engine-state isolation has been implemented before any source acquisition;
5. keep target labels untouched until the source-only feasibility and protocol freeze stages permit them.

The correct scientific posture at this checkpoint is:

> **Do not ask where consequence “really lives” on the board. Ask whether one explicit spatial convention makes the same declared chess evidence easier for a frozen learner to use, under a protocol that prevents unequal information access and post-hoc tuning from deciding the result.**

---

# Current V3 State Update
- V1 freeze -> failed independent audit
- V2 repair -> failed independent re-audit
- V3 repair -> current work (DOWNSTREAM_EXPERIMENT_PROTOCOL_REPAIR_REQUIRED_V3)

---

# Current V4 State Update
- V1 freeze -> failed independent audit
- V2 repair -> failed independent re-audit
- V3 repair -> failed independent re-audit (DOWNSTREAM_EXPERIMENT_PROTOCOL_V3_REAUDIT_FAILED)
- V4 repair -> next task (DOWNSTREAM_EXPERIMENT_PROTOCOL_REPAIR_REQUIRED_V4)

---

# Current V4 Repair
- V4 repair implemented.
- Current status: DOWNSTREAM_EXPERIMENT_PROTOCOL_V4_IMPLEMENTED_REAUDIT_REQUIRED
- Next blocker: INDEPENDENT_DOWNSTREAM_PROTOCOL_REAUDIT_V4_REQUIRED
- Execution blocker: ML_RUNTIME_DEPENDENCY_NOT_YET_SATISFIED

---

# Current V5 Status
- V4 repair -> failed independent re-audit (DOWNSTREAM_EXPERIMENT_PROTOCOL_V4_REAUDIT_FAILED)
- V5 repair -> next task (DOWNSTREAM_EXPERIMENT_PROTOCOL_REPAIR_REQUIRED_V5)

---

# Current V6 Status
- V5 repair -> failed independent re-audit (DOWNSTREAM_EXPERIMENT_PROTOCOL_V5_REAUDIT_FAILED)
- V6 repair -> next task (DOWNSTREAM_EXPERIMENT_PROTOCOL_REPAIR_REQUIRED_V6)

---

# Current V6 Status
- V6 repair -> implemented (DOWNSTREAM_EXPERIMENT_PROTOCOL_V6_IMPLEMENTED_REAUDIT_REQUIRED)
- V6 audit -> next task (INDEPENDENT_DOWNSTREAM_PROTOCOL_REAUDIT_V6_REQUIRED)

---

# Current V7 Status
- V6 re-audit -> failed (DOWNSTREAM_EXPERIMENT_PROTOCOL_V6_REAUDIT_FAILED)
- V7 repair -> next task (DOWNSTREAM_EXPERIMENT_PROTOCOL_REPAIR_REQUIRED_V7)

---

# Current V7 Status
- V7 repair -> implemented (DOWNSTREAM_EXPERIMENT_PROTOCOL_V7_IMPLEMENTED_REAUDIT_REQUIRED)
- V7 audit -> next task (INDEPENDENT_DOWNSTREAM_PROTOCOL_REAUDIT_V7_REQUIRED)

---

# Current ML Runtime Status
- V7 audit -> passed (DOWNSTREAM_EXPERIMENT_PROTOCOL_V7_REAUDIT_PASS)
- ML Runtime Dependency -> next task (ML_RUNTIME_DEPENDENCY_PIN_REQUIRED)

- ML Runtime Dependency -> pinned (ML_RUNTIME_DEPENDENCY_PINNED_REAUDIT_REQUIRED)
- Next task -> INDEPENDENT_ML_RUNTIME_REAUDIT_REQUIRED

- ML Runtime Dependency Re-Audit -> failed (ML_RUNTIME_DEPENDENCY_PIN_REAUDIT_FAILED)
- Next task -> ML_RUNTIME_DEPENDENCY_REPAIR_REQUIRED_V2

- ML Runtime Dependency Repair V2 -> completed (ML_RUNTIME_DEPENDENCY_PIN_V2_IMPLEMENTED_REAUDIT_REQUIRED)
- Next task -> INDEPENDENT_ML_RUNTIME_REAUDIT_V2_REQUIRED

- ML Runtime Dependency Re-Audit V2 -> failed (ML_RUNTIME_DEPENDENCY_PIN_V2_REAUDIT_FAILED)
- Next task -> ML_RUNTIME_DEPENDENCY_REPAIR_REQUIRED_V3

- ML Runtime Dependency Pin V3 -> implemented (ML_RUNTIME_DEPENDENCY_PIN_V3_IMPLEMENTED_REAUDIT_REQUIRED)
- Next task -> INDEPENDENT_ML_RUNTIME_REAUDIT_V3_REQUIRED

- ML Runtime Dependency Pin V3 Re-Audit -> passed (ML_RUNTIME_DEPENDENCY_PIN_V3_REAUDIT_PASS)
- Next task -> EXPLICIT_TARGET_ACQUISITION_AUTHORIZATION_REQUIRED

---

# Current Target Acquisition Status
- TARGET acquisition explicitly authorized
- V1 runner preliminary review failed
- V2 runner repaired/implemented
- TARGET still NOT RUN
- Next task: INDEPENDENT_TARGET_ACQUISITION_IMPLEMENTATION_REAUDIT_V2_REQUIRED

## 2026-08-22 TARGET Acquisition V3 Re-Audit
Hostile audit of the V3 target acquisition runner implementation has passed (`TARGET_ACQUISITION_IMPLEMENTATION_V3_REAUDIT_PASS`). Execution remains paused pending final specific authorization bound to the audited SHA.

## 2026-08-22 TARGET Acquisition V3 Supplemental Re-Audit
Prior audit (ce1c47bf) had insufficient independent execution evidence. Supplemental audit natively performed the required hostile execution matrices. Final authoritative verdict: `TARGET_ACQUISITION_IMPLEMENTATION_V3_REAUDIT_PASS`. Execution remains paused pending final specific authorization bound to the audited SHA.

## 2026-08-22 TARGET Acquisition V1 Execution and Seal
TARGET acquisition explicitly authorized and executed against 33,859 frozen July roots. Artifact successfully captured 1,067,664 typed observations. Raw TARGET artifact cryptographically sealed at `d9b290bd44902559fd98f3b9c17b35b586ff72425cb2783b42cf76e200e81b00`.
Current status: TARGET_ACQUISITION_V1_ACQUIRED_SEAL_REAUDIT_REQUIRED
Next blocker: INDEPENDENT_TARGET_ACQUISITION_EVIDENCE_REAUDIT_REQUIRED
Downstream analysis, labels, and model training remain explicitly UNAUTHORIZED pending the independent evidence re-audit.

## 2026-08-26 TARGET Acquisition Seal V2
V1 seal preliminary review found deterministic seal-layer defects. Raw TARGET acquisition remained unchanged. Seal V2 corrected manifest count semantics and explicit exact-completion equality gates.
Current status: TARGET_ACQUISITION_V1_ACQUIRED_SEAL_V2_REAUDIT_REQUIRED
Next blocker: INDEPENDENT_TARGET_ACQUISITION_EVIDENCE_V2_REAUDIT_REQUIRED
Labels/training remain unauthorized.

## 2026-08-26 Independent TARGET Acquisition Evidence V2 Re-audit
Independent hostile re-audit of the V2 target acquisition evidence seal confirms the seal is structurally and cryptographically exact.
Current status: TARGET_ACQUISITION_EVIDENCE_V2_REAUDIT_PASS
Next blocker: TARGET_LABEL_DERIVATION_PROTOCOL_EXECUTION_AUTHORIZATION_REQUIRED
Labels/training remain explicitly unauthorized.

## 2026-08-26 TARGET Label Derivation Implementation V1
Implemented cp_target_labels.py, run_cp_target_label_derivation.py, and tests.
TARGET evidence V2: AUDITED PASS. Label semantics: FROZEN BY V7.
Real label derivation: NOT RUN / UNAUTHORIZED. Model training: UNAUTHORIZED.
Next blocker: INDEPENDENT_TARGET_LABEL_DERIVATION_IMPLEMENTATION_REAUDIT_REQUIRED.

## 2026-08-26 TARGET Label Derivation Implementation V2
Repaired V1 implementation failures relating to ExperimentResult schemas, strict count gates, determinism, and SHA verification. 
Real July label derivation remains NOT RUN / UNAUTHORIZED.
Status: TARGET_LABEL_DERIVATION_V2_IMPLEMENTED_REAUDIT_REQUIRED.
Next blocker: INDEPENDENT_TARGET_LABEL_DERIVATION_IMPLEMENTATION_REAUDIT_V2_REQUIRED.

## 2026-08-26 TARGET Label Derivation Implementation V3
V3 repaired V2 failures around string-matching ExperimentResult payloads and monkeypatched testing. Implemented unified `ExperimentResult(**...)` parses, canonical JSON-spacing support, immutable expectation dataclasses, and strict determinism via the real `run()` command.
Status: TARGET_LABEL_DERIVATION_V3_IMPLEMENTED_REAUDIT_REQUIRED.
Next blocker: INDEPENDENT_TARGET_LABEL_DERIVATION_IMPLEMENTATION_REAUDIT_V3_REQUIRED.

### Target Label Derivation V4
- Repaired TextIOWrapper output bug and strict target boundary leakage.
- Added deterministic compression assertions and temp-artifact readback guarantees.

### TARGET Label Derivation V6 Status

V5:
TARGET_LABEL_DERIVATION_V5_PREAUDIT_FAIL

V6:
TARGET_LABEL_DERIVATION_V6_IMPLEMENTED_REAUDIT_REQUIRED

Next blocker:
INDEPENDENT_TARGET_LABEL_DERIVATION_IMPLEMENTATION_REAUDIT_V6_REQUIRED

Real July labels:
0 / NOT RUN / UNAUTHORIZED

Model training:
0 / UNAUTHORIZED

### TARGET Label Derivation V6 Re-Audit

V6 Re-Audit:
TARGET_LABEL_DERIVATION_V6_REAUDIT_PASS

Next blocker:
EXPLICIT_TARGET_LABEL_DERIVATION_EXECUTION_AUTHORIZATION_REQUIRED

Real July labels:
0 / NOT RUN / UNAUTHORIZED

Model training:
0 / UNAUTHORIZED

### TARGET Label Derivation V6 Supplemental Re-Audit

V6 Supplemental Re-Audit:
TARGET_LABEL_DERIVATION_V6_REAUDIT_PASS

Next blocker:
EXPLICIT_TARGET_LABEL_DERIVATION_EXECUTION_AUTHORIZATION_REQUIRED

Real July labels:
0 / NOT RUN / UNAUTHORIZED

Model training:
0 / UNAUTHORIZED

### TARGET Label Derivation V6 Supplemental Re-Audit 2

V6 Supplemental Re-Audit 2:
TARGET_LABEL_DERIVATION_V6_REAUDIT_PASS

Next blocker:
EXPLICIT_TARGET_LABEL_DERIVATION_EXECUTION_AUTHORIZATION_REQUIRED

Real July labels:
0 / NOT RUN / UNAUTHORIZED

Model training:
0 / UNAUTHORIZED

previous: EXPLICIT_TARGET_LABEL_DERIVATION_EXECUTION_AUTHORIZATION_REQUIRED
authorization: GRANTED
result if successful: TARGET_LABEL_DERIVATION_V6_MATERIALIZED_SEALED
next blocker: INDEPENDENT_TARGET_LABEL_EVIDENCE_AUDIT_REQUIRED

### TARGET Label Derivation Evidence Seal V2

V1:
TARGET_LABEL_DERIVATION_SEAL_V1_PREAUDIT_FAIL

V6 label artifact:
MATERIALIZED / UNCHANGED / UNAUDITED

V2:
TARGET_LABEL_DERIVATION_V6_MATERIALIZED_SEAL_V2_REAUDIT_REQUIRED

Next blocker:
INDEPENDENT_TARGET_LABEL_EVIDENCE_V2_AUDIT_REQUIRED

Scientific outcome analysis:
UNAUTHORIZED

Model training:
0 / UNAUTHORIZED

### TARGET Label Evidence Audit V2

TARGET_LABEL_EVIDENCE_V2_AUDIT_PASS

Real label artifact:
AUDITED / SEALED / IMMUTABLE

Scientific outcomes:
NOT YET ANALYZED

Model training:
0 / UNAUTHORIZED

Next blocker:
DOWNSTREAM_TRAINING_IMPLEMENTATION_REVIEW_REQUIRED

### TARGET Label Evidence Audit Supplement

TARGET_LABEL_EVIDENCE_V2_AUDIT_PASS

Real label artifact:
AUDITED / SEALED / IMMUTABLE

Scientific outcomes:
NOT YET ANALYZED

Model training:
0 / UNAUTHORIZED

Next blocker:
DOWNSTREAM_TRAINING_IMPLEMENTATION_REVIEW_REQUIRED

### Downstream Representation Efficiency Implementation V1

TARGET_LABEL_EVIDENCE_V2_AUDIT_PASS

Real labels:
AUDITED / SEALED / IMMUTABLE

Downstream implementation:
DOWNSTREAM_TRAINING_IMPLEMENTATION_V1_IMPLEMENTED_REAUDIT_REQUIRED

Real training:
0 / UNAUTHORIZED

Scientific outcome analysis:
NOT PERFORMED / UNAUTHORIZED

Next blocker:
INDEPENDENT_DOWNSTREAM_TRAINING_IMPLEMENTATION_REAUDIT_V1_REQUIRED

### Downstream Representation Efficiency Implementation V2

TARGET_LABEL_EVIDENCE_V2_AUDIT_PASS

Real labels:
AUDITED / SEALED / IMMUTABLE

Downstream implementation:
DOWNSTREAM_TRAINING_IMPLEMENTATION_V2_IMPLEMENTED_REAUDIT_REQUIRED

Real training:
0 / UNAUTHORIZED

Scientific outcome analysis:
NOT PERFORMED / UNAUTHORIZED

Next blocker:
INDEPENDENT_DOWNSTREAM_TRAINING_IMPLEMENTATION_REAUDIT_V2_REQUIRED

### Downstream Representation Efficiency Implementation V3 and V4

TARGET_LABEL_EVIDENCE_V2_AUDIT_PASS

Real labels:
AUDITED / SEALED / IMMUTABLE

V3 downstream implementation:
DOWNSTREAM_TRAINING_IMPLEMENTATION_V3_PREAUDIT_FAIL

V4 downstream implementation:
DOWNSTREAM_TRAINING_IMPLEMENTATION_V4_IMPLEMENTED_REAUDIT_REQUIRED

Real training:
0 / UNAUTHORIZED

Scientific outcome analysis:
NOT PERFORMED / UNAUTHORIZED

Next blocker:
INDEPENDENT_DOWNSTREAM_TRAINING_IMPLEMENTATION_REAUDIT_V4_REQUIRED

### Downstream Representation Efficiency Implementation V5

V5:
DOWNSTREAM_TRAINING_IMPLEMENTATION_V5_PREAUDIT_FAIL

### Downstream Representation Efficiency Implementation V6

V6:
DOWNSTREAM_TRAINING_IMPLEMENTATION_V6_IMPLEMENTED_REAUDIT_REQUIRED

Real training:
0 / UNAUTHORIZED

Scientific analysis:
NOT PERFORMED / UNAUTHORIZED

Next blocker:
INDEPENDENT_DOWNSTREAM_TRAINING_IMPLEMENTATION_REAUDIT_V6_REQUIRED

### Downstream Representation Efficiency Implementation V6

V6:
DOWNSTREAM_TRAINING_IMPLEMENTATION_V6_PREAUDIT_FAIL

### Downstream Representation Efficiency Implementation V7

V7:
DOWNSTREAM_TRAINING_IMPLEMENTATION_V7_IMPLEMENTED_REAUDIT_REQUIRED

Real training:
0 / UNAUTHORIZED

Scientific analysis:
NOT PERFORMED / UNAUTHORIZED

## Post-Checkpoint Updates
- V7 downstream training implementation failed preaudit due to incomplete placeholders.
- V8 downstream training shell, schema, runner, and auth implemented.
- Current Status: `DOWNSTREAM_TRAINING_IMPLEMENTATION_V8_IMPLEMENTED_REAUDIT_REQUIRED`
