import { calculateInfluence, parseFEN } from '@/lib/chess-logic';
import { ChessHeatClient } from '@/components/chess-heat-client';
import type { ChessHeatState } from './actions';

const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

export default async function Home() {
  const board = parseFEN(STARTING_FEN);
  const influenceMatrix = calculateInfluence(board);
  
  const initialState: ChessHeatState = {
    board,
    influenceMatrix,
    insights: 'Enter a FEN string above and click "Visualize" to analyze a chess position and generate AI insights.',
    fen: STARTING_FEN,
    key: Date.now(),
  };

  return <ChessHeatClient initialState={initialState} />;
}
