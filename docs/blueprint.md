# **App Name**: ChessHeat

## Core Features:

- Input Position: Accepts a chess position as input in either a FEN string, or a link to a URL to an X (formerly Twitter) post containing a diagram.
- Calculate Influence: Calculates the net influence each side has over each square on the chessboard. Uses the piece values to weight influence. If a square is empty, assesses the pieces that can move there. If occupied, looks at attackers vs. defenders.
- Highlights: Generates a description that highlights squares where net influence is strongly affected by multiple pieces. A reasoning tool assesses where multiple pieces have influence.
- Render Heatmap: Renders a chessboard, with squares colored according to a color scale indicating positive, negative, or neutral net influence, scaled from darkest red to darkest blue. Pieces rendered normally on top.

## Style Guidelines:

- Primary color: Saturated blue (#4682B4) to represent the core functionality related to the positive influence.
- Background color: Light gray (#F0F0F0) to provide a neutral backdrop.
- Accent color: Analogous violet (#8A2BE2), significantly different from the primary in both brightness and saturation, to create a good contrast, to highlight key interactive elements without distracting from the heatmap itself.
- Font pairing: 'Space Grotesk' (sans-serif) for headlines, 'Inter' (sans-serif) for body.
- Simple, clear icons to represent chessboard positions, and other functionality.
- A clean and efficient layout focusing on the visualization of the chessboard with its heatmap overlay. The input area and the generated highlights are placed below the chessboard for a clear, top-down flow.
- Smooth transitions when the chessboard updates its heatmap and the AI-generated descriptive insights change, to add a layer of subtle dynamism.