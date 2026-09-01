# ChessHeat Decision Log

This file records consequential product, measurement, architecture, and research-integrity decisions so future implementation work does not silently redefine the project.

## D-001 — ChessHeat models consequence structure, not weighted control

**Status:** Accepted

**Decision:**

The primary purpose of ChessHeat is to identify square-level leverage, hazard, and pivotality as board state changes. Attack counts and piece-value-weighted control may be shown as supporting evidence, but they do not define heat.

**Reason:**

The earlier ChessHeat prototype conflated weighted influence with strategic consequence. That approach can label a square neutral or important for the wrong reason and cannot represent indirect positional leverage.

---

## D-002 — Control and importance remain separate data concepts

**Status:** Accepted

**Decision:**

Control geometry must be stored and exposed separately from leverage/consequence evidence.

**Reason:**

A square can be evenly contested yet pivotal, or heavily controlled yet low-impact.

---

## D-003 — Stockfish is an evidence source, not the product model

**Status:** Accepted

**Decision:**

Use Stockfish to provide reproducible evidence about position evaluation and plausible continuations. ChessHeat owns the transformation from that evidence into square-level representations.

**Reason:**

The product's value lies in exposing spatial consequence structure, not in reproducing a standard engine GUI.

---

## D-004 — Preserve raw evidence before composite scoring

**Status:** Accepted

**Decision:**

Move-level engine results, square attribution records, search metadata, geometry events, candidate provenance, and rejected spatial evidence must remain inspectable. No final heat color or scalar may be the only stored result.

**Reason:**

The heat model is a research hypothesis. Preserving raw evidence allows formulas to be revised, compared, and falsified without rewriting the experimental record.

---

## D-005 — No composite pivotality formula in the initial prototype

**Status:** Accepted and reinforced by M8

**Decision:**

Expose separate raw and derived signals until a composite demonstrably adds value over its strongest individual component.

**Reason:**

M8 ablation did not establish a fixed Direct/Recurrence/Bundle fusion that universally dominated. A visually persuasive composite could hide a bad model.

---

## D-006 — Direct attribution is an explicit approximation

**Status:** Accepted

**Decision:**

Initial consequence evidence may be attributed to squares directly involved in legal moves: origin, destination, captured square, promotion/castling/en-passant related squares where applicable.

The system must label indirect causal attribution as unsupported until a validated method exists.

**Reason:**

Many strong chess moves create their important effect elsewhere on the board. Development fixtures confirmed that direct attribution systematically misses important pathways and structural enablers.

---

## D-007 — Heat delta is a first-class primitive

**Status:** Accepted and implemented experimentally

**Decision:**

The measurement architecture must support comparison between consecutive legal positions rather than treating every heatmap as an isolated snapshot.

**Reason:**

The future teaching experience depends on answering: "What did that move change?"

---

## D-008 — Opening instruction should teach strategic reconstruction, not database conformity

**Status:** Accepted; implementation deferred

**Decision:**

Future opening instruction should use board-state changes, heat delta, and curated strategic objectives to teach why moves matter. Leaving theory is not inherently an error if the resulting position preserves sound strategic logic.

**Reason:**

The goal is transferable chess understanding, not rote tree memorization.

---

## D-009 — Generative AI is outside the core measurement pipeline

**Status:** Accepted

**Decision:**

Generative models may eventually explain structured evidence but may not determine engine evaluation, square heat, tactical truth, or causal attribution.

**Reason:**

ChessHeat should remain reproducible and inspectable at the measurement layer.

---

## D-010 — Python analysis core with a versioned evidence boundary

**Status:** Accepted and implemented

**Decision:**

ChessHeat uses a Python-first analysis core that communicates with Stockfish through a narrow engine adapter and emits versioned, structured measurement records. The analysis core must be runnable and testable without any web interface.

The web visualization layer consumes those records. It must not own engine execution, score normalization, legal move generation, square attribution, leverage calculation, hazard calculation, or other measurement semantics.

**Reference flow:**

`legal chess position -> Python analysis core -> Stockfish adapter -> raw engine evidence -> ChessHeat measurement records -> spatial evidence -> web visualization`

**Reason:**

The core research claim concerns measurement, not rendering. Separating the analysis instrument from the interface makes the measurement model independently testable, reproducible, inspectable, and replaceable.

---

## D-011 — Regret is opportunity cost, not causal position delta

**Status:** Accepted

**Decision:**

For centipawn-comparable root moves, define decision regret relative to the best legal root choice:

`R(m) = E* - E(m)`

where all outcomes share the same comparison perspective.

Do not describe baseline-to-child evaluation difference as the consequence caused by a move when the baseline already assumes optimal continuation.

**Reason:**

The engine baseline is itself an optimal-search quantity. Regret is the cleaner interpretation of root-choice sensitivity.

---

## D-012 — Mate evidence remains typed

**Status:** Accepted

**Decision:**

Do not normalize mate outcomes into fake centipawn values. Preserve CP and mate-sensitive evidence as separate typed channels, including zero-optionality state.

**Reason:**

Mate distance and centipawn evaluation are not one linear scale. Converting them into a single fabricated scalar would destroy semantics.

---

## D-013 — Structural geometry is descriptive; association is not causality

**Status:** Accepted

**Decision:**

Represent deterministic geometry changes such as attacks, defenses, rays, blockers, paths, and mobility. When move outcomes differ between moves with and without a geometry event, describe that as association unless the design actually isolates causality.

Perfectly co-occurring structural events may be grouped into event bundles while constituent provenance remains preserved.

**Reason:**

M7 development showed that seemingly meaningful geometry events were often inseparable from other simultaneous changes produced by the same move subset.

---

## D-014 — Spatial shape and position-level amplitude are separate quantities

**Status:** Accepted as architecture; final formulas unresolved

**Decision:**

Keep the question "where is leverage?" separate from "how much leverage exists?"

Represent the conceptual decomposition as:

`S(s | P)` — spatial shape / localization

`A(P)` — position-level decision-leverage amplitude

A future renderer may combine them, but the decomposition must remain inspectable.

**Reason:**

Within-position rank normalization can manufacture relative hotspots in positions whose absolute decision spread is negligible.

---

## D-015 — Severity and decision leverage are different

**Status:** Accepted

**Decision:**

A severe position with at most one legal move has zero root-choice optionality for the purpose of decision-leverage amplitude. Do not equate objectively bad evaluation with high decision leverage.

**Reason:**

Decision leverage measures sensitivity to available choice, not merely how good or bad the position is.

---

## D-016 — ShapeSelectivity-v1 is a frozen development policy, not a chess law

**Status:** Accepted (M8 Freeze)

**Decision:**

Preserve the frozen development predicates:

- Direct: `candidate_fraction >= 0.15`
- Recurrence: `earliest_ply <= 2 AND distinct_line_count >= 3`
- Bundle: `producing_move_count >= 3 AND implicated_region_size <= 15`

Do not retune these thresholds on W-suite hostile evidence. Rejected evidence remains raw evidence rather than being deleted.

**Reason:**

The thresholds were selected after observing development fixtures and therefore cannot be treated as untouched discoveries.

**Implementation note:**

The current helper is an ordered first-success selector and returns one prioritized source / rejection reason rather than a complete independent per-channel state record. M8.6.4 audited this behavior; M8.6.5 corrected earlier forensic wording that had implied stronger channel independence than the helper itself exposes.

---

## D-017 — Experimental invalidity must remain visible

**Status:** Accepted

**Decision:**

Do not silently repair, rename, or rewrite invalid fixtures, contaminated holdouts, failed seals, or falsified hypotheses into cleaner-looking evidence.

Mark them accurately and preserve the original artifacts.

**Reason:**

F4, prior holdout attempts, W-v2 execution, W10/W11 legality failures, and W7's falsified negative-control hypothesis all materially changed the research interpretation.

---

## D-018 — History is a separate research layer until proven otherwise

**Status:** Proposed research constraint

**Decision:**

A future Temporal Ledger may measure historical investment, optionality, conversion, and persistence, but it must not contaminate objective current-state ChessHeat semantics.

For two histories that arrive at the same complete legal state, current-state evidence should agree while historical ledgers may differ.

**Reason:**

This gives the history research a falsifiable boundary and prevents narrative path dependence from changing a state-based measurement without rule-state justification.

---

## D-019 — Candidate-universe definition is part of Recurrence semantics

**Status:** Accepted (M8 Freeze)

**Decision:**

The choice of the candidate universe (e.g., top-5 versus all legal roots) is an intrinsic part of the measurement definition, not merely a performance optimization. `top_n=5` is a frozen development policy for this phase, not an established optimum or universal chess law. Future work must treat candidate-universe design as a fundamental research question.

**Reason:**

On the hostile W development corpus, constraining the future set produced a measurable specificity-coverage tradeoff: it suppressed substantial non-target benchmark geography while also removing some expected benchmark-target geography. That result establishes dependence on the candidate universe, not the optimality of any particular universe.

---

## Open decisions

### O-002 — Reference engine budget

Development work has used fixed node budgets and commonly compared 50k, 100k, and 250k nodes with `Threads=1` and small fixed hash settings. A final production/reference budget remains open.

### O-003 — Mixed CP / mate amplitude

Perspective semantics and type separation are established, but the final mate-sensitive amplitude representation remains unresolved.

### O-004 — Direct square aggregation

Need to determine which direct statistics are useful for presentation without over-rewarding catastrophic singleton blunders.

### O-005 — Hazard definition

Need to determine what qualifies a square as "lava" rather than merely unfavorable, recurring, or contested.

### O-006 — Pivotality evidence

No fixed composite has yet satisfied the requirement to outperform its strongest individual component across representative positions.

### O-007 — Validation method

Need a genuinely untouched validation protocol with legal preflight, multi-square / corridor / disjoint-region ground truth, object-level provenance, and clear separation of fixture invalidity from model failure.

### O-008 — Web visualization stack

The diagnostic viewer exists, but product stack and deployment shape remain intentionally secondary to measurement integrity.

### O-009 — Geographic relevance

What transforms raw geographic evidence into relevance without discarding legitimate rare, deep, broad, or multi-focal leverage?

### O-010 — Consequence-coupled recurrence

Should recurrence be weighted or filtered by how strongly passage through a square distinguishes materially different root outcomes rather than by frequency alone?

### O-011 — Regional representation

Should files, diagonals, corridors, king zones, pawn complexes, and disjoint tactical regions remain first-class objects before projection to squares?

### O-012 — Temporal Ledger

Can move history provide a distinct measurable description of investment, optionality, conversion, and persistence while preserving current-state invariance under true transpositions?

**Status (T1.10a):** The core Temporal Ledger architecture and consequence primitives have been implemented and secured under a strict semantic protocol. It correctly measures historical reappearance and counterfactual outcomes without contaminating current-state amplitude logic.

### D-030 — T1.11 Methodology and Interpretation Limits

**Status:** Accepted

**Decision:**
T1.11 is closed and immutably archived at commit `89d056609b1bfa6fd93c2e3c2f1970e905841c2d`. Its 14/15 SUPPORTED result must NOT be reported as an accuracy or success percentage. The raw JSON outputs must remain exactly as emitted during the sealed one-shot execution.

**Reason:**
A validation artifact is not trustworthy merely because tests pass; the evidence-generation path itself must be tracked, reproducible, mechanically checked, and frozen before consequence observation. The fixtures in T1.11 are not interchangeable trials; they exercise distinct boundaries (e.g. Q4 falsifying a directional prediction, Q11 preserving mate typing, and Q14 proving local structural matches can yield divergent consequence).

### O-013 — Engine-State & Evaluation-Order Robustness (T1.12)

Are CP regret relationships stable to root-evaluation ordering and transposition-table state?

### TARGET Label Derivation V5
- **Status**: ACCEPTED
- **Rationale**: V4 failed due to loose readback equality checking, unpinned zstandard compilation environments, and insufficient test matrices. V5 establishes deterministic runtime environment pins, strict 40-char SHA requirements for execution, and a 45-matrix hostile test sweep.
- **Constraints**: Label derivation is permanently gated behind exact Python binary and dependency byte matching.

V5's "ACCEPTED" status was premature.

Independent pre-audit review subsequently found deterministic implementation
and provenance defects.

Authoritative status for V5:

PREAUDIT_FAIL

Superseded by V6 repair.
