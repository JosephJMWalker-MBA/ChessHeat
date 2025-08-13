import { calculateInfluence, parseFEN } from '@/lib/chess-logic';
import { ChessHeatClient } from '@/components/chess-heat-client';
import type { ChessHeatState } from './actions';

// Start with an empty board for the editor
const STARTING_FEN = '8/8/8/8/8/8/8/8 w - - 0 1';

export default async function Home() {
  const board = parseFEN(STARTING_FEN);
  const influenceData = calculateInfluence(board);
  
  const initialState: ChessHeatState = {
    board,
    influenceData,
    insights: 'Drag pieces onto the board to set up a position. The heatmap and AI analysis will update automatically.',
    fen: STARTING_FEN,
    key: Date.now(),
  };

  return <ChessHeatClient initialState={initialState} />;
}
