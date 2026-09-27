# Control Is Not Consequence: Why Chess Needs a Better Language for Spatial Importance

*ChessHeat Research Note 001*

## The Intuitive Idea

When trying to visualize a chess position, the most intuitive approach is to color the squares based on who attacks them. A square attacked by three white pieces and one black piece gets colored a bright white; a square deep in enemy territory gets painted black. 

This creates a "heatmap" of control. It is visually striking, easy to calculate, and immediately understandable.

## The Problem

Control answers a specific mechanical question: *"Who can reach this square on the next half-move?"*

It does **not** necessarily answer the strategic question: *"How much does this square matter to what happens next?"*

A square can be heavily attacked (high control density) but possess little to no decision leverage—it might be heavily defended, tactically irrelevant, or situated away from the actual conflict. Conversely, a critical square—perhaps the only escape square for a king, or a crucial pivot for a knight maneuver—might be entirely uncontested at the moment, yet possess immense consequence.

In short: attack density does not reliably determine consequence-related importance.

## What ChessHeat Tried

To find a better language for spatial importance, the ChessHeat project systematically dismantled the problem, looking for measurable mathematical objects that could define "importance" (what we call consequence, leverage, hazard, or pivotality).

We tried several approaches:
* **Root Regret (Opportunity Cost):** We measured the centipawn drop if you play the second-best move instead of the best move. This effectively measures the *urgency* or opportunity cost of a decision, but we found it cannot reliably isolate the causal spatial footprint of the piece that moved.
* **Direct Attribution:** We tried assigning importance to the endpoints of tactical moves. This works for simple captures but fails to capture indirect, positional structures.
* **Principal Variation (PV) Recurrence:** We tracked which squares repeatedly showed up in the engine's projected future lines. This provided a distinct future-path signal, but it was highly diffuse and heavily producer/search-conditioned by the engine's internal boundaries.
* **Interventions:** We tried strict matched legal-reply intervention studies to causally identify spatial importance, but the hypothesis was falsified under its preregistered protocol.
* **Geometry:** We measured structural changes away from move endpoints—such as a piece moving to open a diagonal or block a ray. 

## What Survived

We did not discover a magic formula. However, several useful evidence layers survived our rigorous testing:
* We *can* expose structural geometry changes away from move endpoints.
* We *can* separate source orientation, source magnitude, and spatial support.
* We *can* track the opportunity cost (urgency) of deviations.

## What Failed

No universal ownership rule or single "Heat" scalar has earned authority. We have explicitly rejected the idea of compressing all these distinct signals into a single, simplistic heat equation just to make a pretty picture.

**The mathematics needs to earn the color.** Until it does, we preserve the distinctions.

## What Changed

Our research question became much more precise. We stopped asking "What is the heat of this square?" and started asking: *Under a frozen learning regime, does organizing spatial evidence by destinations or by transition-touches yield greater sample efficiency for predicting engine evaluations?*

We moved from seeking a universal truth to measuring representation efficiency.

## The Invitation

We are opening our research process to the community. We need your intuition to stress-test our math.

**Submit positions where your judgment of what matters spatially differs sharply from what a conventional attack/control map emphasizes—in either direction.** 

Tell us what you think matters and why. Can you find a position where the most important square is completely unattacked? Can you find one where a heavily attacked square is completely irrelevant, and an attack map is therefore uninformative? Or conversely, a position where the attack map perfectly captures leverage in a way our metrics might miss?

Bring your counterexamples, alternative interpretations, replications, and criticism. 

See our [Contributing Guide](../../CONTRIBUTING.md) and [Open Questions](../../OPEN_QUESTIONS.md) to get involved.
