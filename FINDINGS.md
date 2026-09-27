# ChessHeat Findings Ledger

ChessHeat preserves negative, falsified, inconclusive, and methodological results as first-class research findings. The governing invariant remains: **The mathematics needs to earn the color.**

Below is a curated index of mature findings, supported by the rigorous constraints and boundaries documented in our research architecture.

## Mature Findings

### 1. Control Is Not Consequence
A square may be under heavy attack density (control) but possess little decision leverage. Conversely, a square can be evenly contested yet highly consequential. Attack density does not reliably determine consequence-related importance.
*Status: Supported by M1-M8 and T1/T2 investigations.*
*Further Reading: [Control Is Not Consequence](docs/notes/001-control-is-not-consequence.md)*

### 2. Opportunity Cost (Regret) is Not a Causal Move Delta
Measuring the centipawn drop of the second-best move (regret) effectively measures the urgency or opportunity cost of a decision. However, it cannot reliably isolate the causal spatial footprint of the piece that moved.
*Status: Established in early Milestone research.*

### 3. The Diffuseness of Principal Variation (PV) Recurrence
Tracking which squares recur in an engine's Principal Variation provides a distinct future-path signal. However, this signal can be diffuse and is heavily producer/search-conditioned by the engine's internal pruning heuristics and horizons.
*Status: Established.*

### 4. Structural Geometry Exposes Off-Endpoint Impact
Chess consequence frequently occurs away from the physical endpoints of a move (e.g., opening a diagonal, cutting off a retreat, blocking a ray). Structural geometry measurements can successfully expose these off-endpoint changes, though they have not yet earned status as a universally valid measure of overall consequence.
*Status: Supported by event-bundle and geometry delta research.*

### 5. Strict Matched Legal-Reply Intervention is Not Identified
An attempt to causally identify spatial importance via a strict matched legal-reply intervention study was falsified under its preregistered protocol.
*Status: Falsified (T3b).*

### 6. Objective Square Attribution Remains Unsolved
Current axioms fail to universally identify objective square attribution. Distinctions between source orientation, source magnitude, and spatial-support convention must be maintained rather than collapsed into a single metric.
*Status: Ongoing research focus.*
