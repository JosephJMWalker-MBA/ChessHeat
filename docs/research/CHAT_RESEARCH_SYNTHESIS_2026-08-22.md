# Chat Research Synthesis — 2026-08-22

## Status

This document is a **non-authoritative research synthesis and future-work input** extracted from an external research conversation. It does **not** amend, supersede, reinterpret, or relax any frozen ChessHeat semantic contract, preregistration, audit verdict, acquisition authorization, execution seal, or claim ceiling.

Use it as a source of hypotheses, falsifiers, and prospective diagnostics when future protocol changes are considered. If any item conflicts with an authoritative freeze or audit, the authoritative repository artifact wins unless a new prospective decision explicitly changes the protocol.

## Why preserve this separately

The conversation repeatedly generated useful external-evidence pressure tests while the repository was moving rapidly. Many of those questions were later resolved by the repository itself. Preserving only the final chat message would lose that provenance; copying them into a frozen preregistration would contaminate the distinction between prospectively frozen decisions and later commentary.

The durable distinction is:

- **authoritative protocol/freeze/audit artifacts** = what ChessHeat has actually committed to;
- **this synthesis** = what external research suggested should be tested, falsified, or watched next.

## Research findings worth retaining

### 1. Preserve branch identity before aggregation

Early external comparison with tree-search and causal-abstraction work supported the architectural decision to retain state-action / root-branch identity before recurrence or consequence aggregation.

Retained hypothesis:

> Branch-conditioned consequence can contain information that is irrecoverable after branch collapse, so branch-preserved evidence should remain upstream of projection and visualization.

Repository impact: this is now largely absorbed into the semantic and data-model architecture and should be treated as historical support, not a new open task.

### 2. Square addressability is not automatically the semantic primitive

External graph/relational reasoning and chess-model evidence suggested a useful distinction:

`addressable square substrate != semantic measurement primitive`

Squares can remain excellent projection coordinates while relations, regions, paths, blockers, rays, king zones, pawn complexes, or multi-square components may sometimes be better intermediate evidence subjects.

Retained falsifier:

> A relational/regional subject has not earned first-class measurement status if its branch-discrimination or consequence-association information can be reconstructed from the underlying square-event representation under matched evidence and provenance.

Repository impact: later T2 work closed the specific ray/blocker privileged-basis hypothesis without establishing universal relational primacy. Preserve this only as a general architectural caution against assuming that visualization coordinates define the measurement ontology.

### 3. Matching feasibility must be about overlap breadth, not only match count

When T3b exact same-origin move-form matching was active, external matching literature supported prospective, outcome-blind exact/coarsened-exact design and the repository's no-rescue posture.

Retained caution:

> Aggregate matchability can hide selection-by-matchability. A matcher may produce many pairs while concentrating them in a narrow subset of positions, move forms, phases, or piece classes.

Retained falsifier:

> If strictly matchable events are heavily concentrated in a narrow rule-only subset, resulting intervention conclusions describe that selected subset rather than destination sensitivity generally.

Repository impact: T3b is now historical/closed. Keep this as methodology provenance for any future matching experiment.

### 4. Semantic root identity and statistical independence are different concepts

External correlated-data and leakage literature supported a distinction that became important during CP-only preregistration:

`semantic evidence unit = root`

but potentially

`statistical dependence cluster >= root`

Distinct roots can still be correlated through games, repeated opening structures, transpositions/equivalent states, or acquisition lineage.

Retained falsifier:

> A representation advantage that exists under root-random splitting but disappears under prospectively defined dependence-group-disjoint splitting is evidence about corpus structure rather than robust representation efficiency.

Repository impact: this concern appears to have been absorbed into the current protocol through one-root-per-game construction and conservative transposition-equivalence grouping for train/validation/test separation. Do not reopen it unless those mechanics change.

### 5. Use leakage-prevention grouping at the actual split boundary

A later chat pressure test specifically noticed that conservative transposition-equivalence grouping existed in the preregistration while an older split description referred to canonical-root identity only.

Retained principle:

> A leakage-prevention identity only protects inference if it is actually enforced at train/tune/test partition construction.

Repository impact: current CP preregistration now states that partitions are split by conservative transposition-equivalent group identity while canonical root identity remains the semantic root identifier. This chat finding is therefore resolved and preserved here only as provenance.

### 6. Deeper same-engine target is conditional evidence, not ground truth

External Stockfish/search literature and ranking-distillation analogies supported the repository's claim ceiling that Stockfish 18 at 250k nodes is a deeper target instrument, not objective consequence or truth.

Retained hypothesis:

> A fixed increase in search budget is scientifically useful only if it produces enough nontrivial ordering information to discriminate candidate representations.

This is the most relevant unresolved contribution from the conversation at the current frontier.

### 7. Target-label adequacy / identifiability diagnostic

Before model training, the conversation proposed an outcome-blind descriptive audit of SOURCE-to-TARGET label structure after target acquisition.

The purpose is **not** to retune the already frozen 50k/250k instruments, representations, learner, or Heat semantics. The purpose is to establish whether the frozen target contrast is sufficiently informative to interpret a later representation-efficiency result.

Candidate diagnostics:

- SOURCE versus TARGET pair-order agreement rate;
- reversal rate;
- tie-transition rates;
- per-root prevalence of disagreement;
- label entropy / degeneracy across frozen partitions;
- breadth of disagreement across prospectively chosen **rule-only, outcome-blind** root or move characteristics.

Interpretation caution:

- near-total SOURCE/TARGET agreement can make all representations saturate, so a null operator difference would not strongly establish equal representation efficiency;
- disagreement concentrated in a very narrow rule-derived subset can make an apparent operator advantage primarily characterize the topology of deeper-search revisions rather than broad spatial representation efficiency.

Strong identifiability falsifier:

> If the frozen TARGET contrast has near-zero incremental ordering information, or if nearly all SOURCE-to-TARGET revisions are concentrated in a narrow prospectively describable rule-only subset, the experiment may be insufficiently discriminative for the intended representation-efficiency interpretation.

Critical governance constraint:

> These diagnostics should be descriptive/interpretive only unless a future prospective protocol explicitly says otherwise. They must not become a post-target mechanism for changing the target budget, operators, learner, split, training budgets, or primary contrast.

## Current best next research question from this thread

**Q#** After authorized TARGET acquisition but before any model fitting, should ChessHeat freeze a target-label-adequacy report whose only function is to characterize the breadth and entropy of 50k-to-250k ordering disagreement, with an explicit prohibition on using that report to retune the frozen experiment?

This question is intentionally subordinate to the repository's current operational blocker/authorization state. It should not authorize acquisition, training, or protocol modification by itself.

## #C — principal alternative explanation to retain

A future result such as `AULC_D > AULC_T` can be generated by the *topology of source-to-target revisions* rather than a broad intrinsic advantage of destination organization.

Example: if deeper Stockfish revisions overwhelmingly occur in checks, promotions, tactical captures, or another narrow rule-derived class, one representation may align more directly with that class. The positive result would remain valid under the frozen experiment, but its scientific interpretation should be correspondingly narrow.

## Resolved versus still-useful map

Resolved/absorbed by repository:

- branch identity preservation;
- exact provenance-first data modeling;
- conservative transposition leakage grouping;
- distinction between target instrument and objective consequence;
- exact matching/no-rescue methodology from T3b;
- no privileged ray/blocker measurement basis.

Still useful as future development input:

- target-label adequacy / identifiability audit before learner fitting;
- explicit interpretation of disagreement breadth and entropy;
- maintaining the distinction between measurement ontology and visualization coordinates;
- treating correlation/leakage and overlap as recurring experiment-design questions whenever future populations or matchers change.

## Placement rule

Do not copy this document wholesale into `CP_ONLY_REPRESENTATION_EFFICIENCY_PREREGISTRATION.md`, a protocol freeze, or an audit result. If a retained hypothesis becomes a real protocol requirement, promote only the exact prospectively approved rule into a new authoritative artifact and cite this synthesis as historical motivation if useful.
