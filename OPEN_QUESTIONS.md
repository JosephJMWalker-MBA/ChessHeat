# Open Questions & Active Research

ChessHeat welcomes community participation, particularly where human intuition diverges from our current measurement models or where domain experts can stress-test our findings.

Outside participation must never silently mutate a frozen experiment. Instead, community exploration informs Candidate Questions, which may graduate to formalized protocols and frozen experiments. (See [CONTRIBUTING.md](CONTRIBUTING.md) for details).

## Active Community Challenges

### 1. The Control vs. Consequence Divergence
**The Problem:** Standard chess heatmaps assume that control (who attacks a square) equals importance. We have found this to be false.
**The Ask:** Submit FEN positions where your judgment of what matters spatially differs sharply from what a conventional attack/control map emphasizes—*in either direction*. Tell us what you think matters and why. Can you find positions where attack density accurately maps to leverage, or conversely, where the most important square is entirely unattacked?
**How to contribute:** Open a [Counterexample Submission](.github/ISSUE_TEMPLATE/counterexample_submission.md) issue.

### 2. Methodological Critique of Transposition Grouping
**The Problem:** In our CP-only representation-efficiency experiments (V16/V17), we rely on one-root-per-game construction and conservative transposition-equivalent split grouping to address statistical dependence and data leakage.
**The Ask:** We invite statisticians to critique this methodology. Are there edge cases where transposition-equivalent grouping is insufficient to prevent test-set contamination?
**How to contribute:** Open a GitHub Discussion.

### 3. Alternative Explanations for "Diffuseness" in PV Recurrence
**The Problem:** We observe that Principal Variation recurrence yields diffuse signals. 
**The Ask:** Are there engine-specific parameters (e.g., in Stockfish 18) that artificially inflate this diffuseness? How can we better separate genuine spatial ambiguity in the position from search-heuristic artifacts?
**How to contribute:** Open a GitHub Discussion.
