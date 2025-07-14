// src/app/actions.ts
'use server';

import { generateInsights } from '@/ai/flows/generate-insights';
import { calculateInfluence, parseFEN } from '@/lib/chess-logic';
import type { Board, InfluenceMatrix } from '@/lib/chess-logic';
import { z } from 'zod';

export interface ChessHeatState {
  board: Board;
  influenceMatrix: InfluenceMatrix;
  insights: string;
  fen: string;
  error?: string;
  key: number;
}

const fenSchema = z.string().refine(
  (fen) => {
    // A basic FEN validation regex
    const parts = fen.split(' ');
    if (parts.length < 1) return false;
    const ranks = parts[0].split('/');
    if (ranks.length !== 8) return false;
    return ranks.every(rank => /^[1-8prnbqkPRNBQK]{1,8}$/.test(rank.replace(/[1-8]/g, m => '1'.repeat(parseInt(m, 10)))));
  },
  {
    message: "Invalid FEN string format.",
  }
);


export async function getChessHeatmap(
  currentState: ChessHeatState,
  formData: FormData
): Promise<ChessHeatState> {
  const fenInput = formData.get('fen') as string;

  if (!fenInput) {
    return { ...currentState, error: 'Please provide a FEN string.' };
  }
  
  const validation = fenSchema.safeParse(fenInput.split(' ')[0]);

  if (!validation.success) {
      return { ...currentState, error: 'Invalid FEN string. Please check the format.' };
  }

  try {
    const board = parseFEN(fenInput);
    const influenceMatrix = calculateInfluence(board);
    const { insights } = await generateInsights({ netInfluenceMatrix: influenceMatrix });

    return {
      board,
      influenceMatrix,
      insights,
      fen: fenInput,
      key: Math.random(),
    };
  } catch (e) {
    console.error(e);
    const errorMessage = e instanceof Error ? e.message : 'An unknown error occurred.';
    return { ...currentState, error: `Error processing FEN: ${errorMessage}` };
  }
}
