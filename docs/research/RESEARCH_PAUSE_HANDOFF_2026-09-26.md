# ChessHeat Research Pause / Restart Handoff — 2026-09-26

## Status

This document is a **non-authoritative continuity and restart handoff**.

It does **not** amend, supersede, reinterpret, or relax any frozen semantic contract, preregistration, protocol freeze, audit verdict, execution seal, authorization state, or claim ceiling.

If this document conflicts with an authoritative protocol/freeze/audit artifact, the authoritative artifact wins.

The governing invariant remains:

> **The mathematics needs to earn the color.**

## Why research is paused

Active ChessHeat research is intentionally paused as of 2026-09-26.

The immediate operating priority is to obtain paying customers for Masters Consulting Group so that future research can be funded from earned revenue. The implementation/research collaborator referred to in recent continuity work as Antigravity has also been unavailable, which is the practical reason the repository has not advanced beyond the current production-execution blocker.

This pause is a resource/execution discontinuation. It is **not** technical invalidation, economic invalidation of the ChessHeat hypothesis, or evidence against the frozen experiment.

Do not reinterpret inactivity during this period as a scientific result.

## Repository frontier at pause

Repository HEAD observed immediately before this handoff:

```text
c73aae3a8b0fb13bdd966d119a5f51aa4b77a78e
Audit downstream production execution v16
```

The authoritative V16 state remains the live execution frontier.

Real downstream training has not been authorized/completed under that verdict, and the scientific representation-efficiency result remains unopened.

Older operational language in files such as `AGENTS.md`, `RESEARCH_CONTINUITY_CHECKPOINT_2026-08-16.md`, and portions of `NEXT_WORK_MAP.md` may describe earlier blockers such as TARGET acquisition or preregistration work. Preserve those documents as historical provenance. Later authoritative acquisition/recovery/freeze/audit artifacts govern the later operational state.

## Resolved work that should stay resolved

Do not reopen these merely to seek a favorable result:

- branch identity must be preserved before aggregation where consequence comparisons require it;
- square addressability does not establish that squares are the privileged semantic measurement primitive;
- the tested ray/blocker privileged-basis hypothesis is closed;
- T3b matching/intervention work is closed under its recorded verdicts;
- semantic root identity is distinct from statistical dependence;
- one-root-per-game construction and conservative transposition-equivalent split grouping address the current dependence/leakage concern;
- leakage-prevention grouping must be enforced at the actual split boundary;
- source and target engine state isolation is frozen/audited;
- the TARGET instrument is Stockfish 18 at the frozen deeper search budget and is **not ground truth**;
- authoritative TARGET acquisition/reconstruction/recovery provenance was resolved before the V16 frontier;
- the V6 TARGET-label artifact was recovered with its authoritative identities;
- no objective square ownership, universal Heat amplitude, universal representation superiority, or causal square importance has been earned.

## Frozen scientific object

The active experiment remains a **learner-relative CP-only representation-efficiency experiment**.

The primary question is whether, under the frozen learner/training regime and equalized underlying move information, destination-only organization `mu_D` or transition-touch organization `mu_T` yields greater sample efficiency for predicting the held-out ordering produced by the frozen deeper TARGET instrument.

Preserve these distinctions:

```text
semantic root identity != statistical dependence
measurement ontology != visualization coordinates
source evidence != target-instrument labels
association != causality
intervention sensitivity != causal identification
target-instrument utility != objective truth
where leverage is != how much leverage exists
shape != amplitude
information gain != representation utility
non-significance != equivalence
```

No post-TARGET diagnostic described below authorizes changing target budgets, spatial operators, learner, splits, training budgets, Heat semantics, or primary contrasts.

## Live implementation blocker: V17

The next implementation work should begin by re-reading the V16 hostile audit rather than relying on this summary.

The accumulated post-V16 research narrowed the required execution contract substantially.

### 1. Fresh and resumed evidence need one semantic validator

Byte/hash integrity is necessary but insufficient:

```text
byte-integrity != scientific-result validity
```

A durable/resumed worker result must satisfy the same scientific validity contract as a freshly returned worker result.

The preferred invariant is conceptually:

```text
validate_worker_result(job_spec, result)
```

applied identically regardless of whether the result was produced in the current process or recovered after interruption.

Validation should cover every scientifically material field required by the frozen runner, including expected root/loss coverage, finite values, effective root population identity, model-state identity, validation-trace consistency, epoch bounds, and the frozen best-epoch/earliest-minimum rule.

### 2. At-least-once computation is acceptable; evidence admission must be unique

The project does not need to prove that a worker can physically execute only once after crashes.

The stronger and more useful requirement is:

```text
one frozen job identity -> one admissible canonical scientific result
```

A retry may recompute a job. Repeated execution must either reproduce the same scientifically material canonical payload or fail closed.

Do not let race order decide scientific provenance.

### 3. Publication must be atomic and no-clobber

A check such as:

```text
if destination does not exist:
    replace(destination)
```

does not establish no-clobber semantics because of the TOCTOU interval.

The production platform/filesystem should use a demonstrably exclusive publication primitive or equivalent protocol. An already existing canonical result means verify/reuse or fail; it must never be silently replaced.

The exact primitive is an implementation choice and must be validated on the actual production environment rather than assumed from another OS/filesystem.

### 4. Crash/restart must be proven at parent level

A hostile integration test should demonstrate:

1. an actual interruption after some durable predecessors exist;
2. restart in a fresh worker/process context;
3. reuse only of semantically valid durable results;
4. recomputation of missing/invalid results;
5. a final complete manifest equivalent to an uninterrupted reference under the frozen runtime;
6. no-clobber behavior under concurrent publication attempts.

### 5. Complete experiment or no scientific experiment

The final authorization gate should require the exact expected complete validated production manifest before scientific analysis is permitted.

For the currently frozen production plan this has been discussed as the expected **160/160 validated jobs**.

The 7,200-second watchdog is therefore best treated as a liveness/resource-feasibility constraint:

```text
timeout -> abort/incomplete experiment
```

not:

```text
timeout -> omit slow condition -> analyze survivors
```

If execution policy must change for hardware feasibility, the change must be global/condition-invariant, prospectively recorded, and adjudicated against the frozen protocol before seeing a favorable scientific result.

## Scientific frontier after the execution gate

Once the production runner is legitimately authorized, the highest-leverage scientific question is no longer merely whether TARGET labels have high marginal entropy.

### 1. Marginal TARGET entropy is weak evidence

Because legal-alternative pairs have a canonical FIRST/SECOND serialization, a balanced FIRST_BETTER / SECOND_BETTER distribution can have high entropy even when SOURCE and TARGET almost always agree.

Therefore:

```text
TARGET label entropy != incremental deeper-search information
```

The more relevant descriptive object is SOURCE-to-TARGET revision.

Let `d_X` be SOURCE ordering and `Y` the TARGET class. Useful descriptive quantities include the revision-type distribution and conditional uncertainty such as `H(Y | d_X)`, without elevating any one entropy threshold into a new gate.

### 2. Pair mass is not breadth

A pooled pair-level reversal/disagreement percentage can be dominated by pair-rich roots.

Preserve the experiment's existing ontology:

- canonical root remains the principal statistical sampling unit;
- conservative transposition-equivalent grouping remains a dependence/leakage protection identity;
- the latter should not silently replace the former as the estimand.

Useful descriptive breadth therefore includes:

- pair-level revision structure;
- root-level prevalence/distribution of revision;
- concentration across conservative dependence groups as a secondary sensitivity diagnostic;
- breadth across prospectively specified rule-only/outcome-blind characteristics.

### 3. Breadth and entropy are not learnability

Even broad SOURCE-to-TARGET disagreement can be effectively unpredictable under the frozen admissible information and learner.

Preserve the hierarchy:

```text
revision exists
-> revision is broadly distributed
-> revision contains learner-accessible systematic structure
-> spatial organizations may differ in sample efficiency
```

Do not add a new post-TARGET learner merely to rescue or diagnose the experiment. The frozen baselines and learning curves already provide the proper learner-relative evidence.

### 4. The common baseline is scientifically informative

The frozen nonspatial baseline `B_daS` is not merely a nuisance comparator.

Its absolute learning behavior helps distinguish:

```text
TARGET contains predictable structure under common evidence
```

from:

```text
neither tested spatial organization adds sample-efficiency value
```

A pattern such as strong `B_daS` learning with `D` and `T` near `B_daS` would be materially different from a null D-vs-T contrast where every condition remains near irreducible uncertainty.

However, strong aggregate `B_daS` performance can still be driven by SOURCE/TARGET agreement and therefore does not by itself prove that revisions are predictable.

### 5. Agreement/revision slices are descriptive, not prospective tasks

Define:

```text
R = 1[Y != d_X]
```

A post-hoc NLL slice conditional on `R=1` is legitimate descriptive context, but `R` is TARGET-derived. Performance within that slice is **not** automatically an estimate of prospective revision learnability.

Do not confuse:

```text
performance after being told which cases revised
```

with:

```text
ability to identify revision-prone cases prospectively
```

### 6. A possible secondary prospective diagnostic from existing predictions

Without training another model, an already-frozen three-class predictive distribution can be collapsed into a probability that TARGET revises SOURCE:

```text
p_hat(R=1) = 1 - p_hat(Y=d_X)
```

If this diagnostic is ever used, its scoring/aggregation/interpretation should be prospectively frozen before results are opened and remain secondary/descriptive. It must not modify the primary statistic or trigger retuning.

This is a candidate restart question, not an already-authorized amendment.

### 7. TEST should remain a lockbox

TARGET acquisition does not imply that TARGET labels are permissible to inspect everywhere before fitting.

The clean sequence is:

```text
prospectively freeze adequacy definitions
-> TRAIN/VALIDATION descriptive work where authorized
-> frozen training / VALIDATION model selection
-> single authorized TEST opening
-> primary TEST result + prospectively defined descriptive adequacy context
```

Do not spend TEST blindness early merely to make the experiment easier to interpret.

### 8. Interpretation rules should be symmetric

Adequacy diagnostics must not become a post-hoc rhetorical escape hatch.

Before seeing outcomes, future work should specify how low/broad/concentrated/heterogeneous SOURCE-to-TARGET revision structure constrains interpretation regardless of whether the frozen D-vs-T outcome favors D, favors T, or is null/non-significant.

The diagnostics may constrain claim strength. They may not rescue a preferred representation.

## Recommended restart sequence

When ChessHeat resumes:

1. Read `AGENTS.md`, the continuity checkpoint, `NEXT_WORK_MAP.md`, the active CP-only preregistration/freeze, all later audits through V16, and `CHAT_RESEARCH_SYNTHESIS_2026-08-22.md`.
2. Treat stale operational text in older orientation documents as historical where later authoritative artifacts supersede it; do not alter historical provenance merely to make the repository look cleaner.
3. Re-audit the exact current HEAD before assuming this handoff is still current.
4. Complete and hostile-test the V17 production-execution repair.
5. Do not authorize scientific analysis until the exact expected complete validated manifest exists under the authoritative gate.
6. Before opening scientific results, prospectively freeze any secondary adequacy diagnostics and their symmetric interpretation rules that are still desired and permitted.
7. Preserve TEST blindness until its authorized opening.
8. Run the frozen experiment without post-TARGET retuning.
9. Interpret SOURCE-to-TARGET disagreement quantity, breadth, learner-accessible structure, and D-vs-T representation efficiency as distinct layers.
10. Keep the claim ceiling instrument-conditioned and learner-relative.

## Best restart questions

### Implementation P1

> Can the repaired production runner make interruption history irrelevant to evidence admissibility by applying one semantic validator to fresh and resumed results, enforcing immutable/no-clobber canonical publication, and refusing scientific authorization without the exact complete validated job manifest?

### Scientific P1 after implementation authorization

> Under the already-frozen learner and predictions, does SOURCE-to-TARGET revision have enough root-level breadth and learner-accessible structure to make the D-vs-T sample-efficiency contrast interpretable, while keeping TARGET as an instrument rather than objective truth?

### Secondary diagnostic candidate

> Can the frozen three-class probabilities be collapsed prospectively into `p_hat(R=1) = 1 - p_hat(Y=d_X)` and scored root-weightedly as a secondary diagnostic of revision recognition without training another model or changing any frozen primary analysis?

## Pause classification

Current discontinuation category:

```text
ORGANIZATIONAL / RESOURCE DISCONTINUATION
SCIENTIFIC QUESTION UNRESOLVED
IMPLEMENTATION GATE UNRESOLVED
NO NEGATIVE SCIENTIFIC VERDICT IMPLIED
```

The correct action during the pause is preservation, not reinterpretation.
