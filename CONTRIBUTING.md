# Participating in ChessHeat

ChessHeat is an open research program, but it maintains strict boundaries to protect the integrity of its scientific protocols. 

**Outside participation must never silently mutate an already-frozen experiment or protocol.**

However, we actively seek community critique, domain expertise, and counterexamples to shape *future* experiments. You do not need to write code to contribute.

## The Public Research Lifecycle

We observe a strict sequence for integrating community feedback into the research record:

1. **Community Exploration:** A contributor submits a counterexample, a statistical critique, or an alternative interpretation via GitHub Issues or Discussions.
2. **Candidate Question:** The project acknowledges and refines the input into a discrete research question.
3. **Formalized Protocol:** A preregistration or measurement protocol is drafted specifically targeting the question.
4. **Frozen Experiment:** The protocol is frozen, and the test is executed.
5. **Published Finding:** The result (positive, negative, or inconclusive) is published in `FINDINGS.md` and as a Research Note, crediting the community catalyst.

## How You Can Contribute (Non-Code)

### 1. Chess Players & Domain Experts
* **Counterexample Positions:** Use our [Counterexample Submission Template](.github/ISSUE_TEMPLATE/counterexample_submission.md) to provide FENs where engine evaluations, standard attack maps, or ChessHeat assumptions fail to capture the true spatial leverage of the position.
* **Critique:** Tell us where our pedagogical or structural interpretations of chess events feel disjointed from actual play.

### 2. Statisticians & Data Scientists
* **Methodological Critique:** Review our data-leakage prevention (e.g., transposition grouping) and statistical baselines.
* **Experimental Design:** Propose formal ways to test specific hypotheses about spatial consequence.

### 3. Engine Enthusiasts
* **Instrument Limits:** Help us understand the edge cases of Stockfish's node allocation, hashing behavior, or search-depth anomalies that could contaminate our measurements.

### 4. Visualization Designers
* **Alternative Mappings:** We produce typed JSON evidence layers (raw data). We invite designers to experiment with alternative ways to project this data without compromising the underlying math.

### 5. Developers
* **Architecture & Efficiency:** Review our Python analysis core and streaming architectures. Note: Implementation contributions must respect the frozen protocols and not alter measurement semantics.

## Getting Started
Check [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) to see where we currently need the most help.
