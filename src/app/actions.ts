// src/app/actions.ts
'use server';

import { generateInsights } from '@/ai/flows/generate-insights';
import { calculateInfluence, parseFEN } from '@/lib/chess-logic';
import type { Board, InfluenceData } from '@/lib/chess-logic';
import { z } from 'zod';

export interface ChessHeatState {
  board: Board;
  influenceData: InfluenceData;
  insights: string;
  error?: string;
  key: number;
}

// This function is kept for now to handle the board updates, but FEN is no longer the primary driver.
// The board state is now built on the client and the FEN is generated from it for the action.
// We will remove the FEN dependency entirely in subsequent steps.
const fenSchema = z.string().refine(
  (fen) => {
    const parts = fen.trim().split(/\s+/);
    if (parts.length < 1) return false;

    const [piecePlacement] = parts;
    const ranks = piecePlacement.split('/');
    if (ranks.length !== 8) return false;
    for (const rank of ranks) {
      let count = 0;
      for (const char of rank) {
        if (/[1-8]/.test(char)) {
          count += parseInt(char, 10);
        } else if (/[prnbqkPRNBQKXT]/.test(char)) {
          count++;
        } else {
          return false;
        }
      }
      if (count !== 8) return false;
    }
    return true;
  },
  {
    message: "Invalid FEN string format generated internally.",
  }
);


export async function getChessHeatmap(
  currentState: ChessHeatState,
  formData: FormData
): Promise<ChessHeatState> {
  const fenInput = formData.get('fen') as string;

  if (!fenInput) {
    // This case should ideally not be hit with the new editor flow
    return { ...currentState, error: 'Internal error: No board data provided.' };
  }
  
  const validation = fenSchema.safeParse(fenInput);

  if (!validation.success) {
      return { ...currentState, error: 'Internal error: Invalid board state.' };
  }

  try {
    const board = parseFEN(fenInput);
    const influenceData = calculateInfluence(board);
    
    // Prepare a serializable version of detailed influence for the AI
    const serializableDetailedInfluence = influenceData.detailedInfluence.map(row => 
      row.map(square => ({
        attackers: square.attackers.map(a => a.piece),
        defenders: square.defenders.map(d => d.piece),
      }))
    );
    
    const { insights } = await generateInsights({ 
      netInfluenceMatrix: influenceData.netInfluence,
      detailedInfluence: serializableDetailedInfluence,
    });

    return {
      board,
      influenceData,
      insights,
      key: Math.random(),
    };
  } catch (e) {
    console.error(e);
    const errorMessage = e instanceof Error ? e.message : 'An unknown error occurred.';
    return { ...currentState, key: Math.random(), error: `Error processing board: ${errorMessage}` };
  }
}
