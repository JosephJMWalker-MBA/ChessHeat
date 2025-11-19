# ChessHeat Project Overview

## Project Goal

The primary goal of the ChessHeat project is to create a modern, interactive, and insightful chess analysis tool. The application is designed for chess players of all levels to visualize and understand the complex tactical dynamics of any given chess position.

The core features are:
1.  **Interactive Board Editor:** Allow users to easily set up any chess position by dragging and dropping pieces.
2.  **Influence Heatmap:** Provide a real-time, color-coded visualization of square control on the chessboard, showing the balance of power between White and Black.
3.  **AI-Powered Analysis:** Leverage a generative AI model to analyze the board's influence data and provide actionable tactical insights about key squares, potential threats, and positional advantages.
4.  **Accessible UI:** Ensure the application is usable for everyone, including keyboard and screen-reader users, with a clean and intuitive interface.

Ultimately, ChessHeat aims to be a powerful study aid that helps players deepen their understanding of piece coordination, tactical pressure, and positional play.

## Development Steps Taken

1.  **Initial Setup:**
    *   The project was scaffolded as a Next.js application using TypeScript.
    *   Styling was established with Tailwind CSS, and UI components from the ShadCN library were integrated.
    *   Google's Genkit was set up to handle the generative AI functionality.

2.  **Core Chess Logic Implementation:**
    *   A robust `parseFEN` function was created to translate Forsyth-Edwards Notation (FEN) strings into an internal board representation.
    *   The central `calculateInfluence` function was developed to compute control data for every square, identifying all attackers and defenders. This logic was refined to correctly handle the blocking behavior of sliding pieces (rooks, bishops, queens) and the forward-only attack of pawns.
    *   Unit tests were added using `vitest` to ensure the correctness of FEN parsing and influence calculations, preventing future regressions.

3.  **AI-Powered Insights:**
    *   An AI flow was defined using Genkit to analyze the board's influence matrix.
    *   The prompt instructs the AI to act as an expert chess analyst, identifying tactical motifs like contested squares, forks, pins, and overloaded pieces.

4.  **Frontend and User Experience:**
    *   **Board Interaction:** The application was transformed from a static FEN-input tool into a fully interactive board editor where users can drag and drop pieces to set up positions.
    *   **Heatmap Visualization:** The heatmap coloring logic was significantly improved. It now uses a symmetric, more accessible color scale (blue for white, red for black) to accurately represent the magnitude of influence for both sides.
    *   **Accessibility:** Major accessibility enhancements were made. Board squares were converted from `<div>`s to interactive `<button>`s, making them accessible to keyboard and screen reader users. Square details, previously only on hover, were moved to a selectable panel.
    *   **Layout & UI:** The entire layout was refactored to prioritize the interactive board. A collapsible sidebar was introduced to house the AI insights and square details, creating a cleaner and more focused user experience.
    *   **Board Orientation:** A critical feature was added to allow users to flip the board and view the position from Black's perspective, providing essential analysis flexibility.

5.  **Build and Configuration:**
    *   Addressed several Next.js configuration issues, including resolving port conflicts and handling cross-origin request errors in the development environment, to ensure a stable server.
