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
  fen: string;
  error?: string;
  key: number;
}

const fenSchema = z.string().refine(
  (fen) => {
    const parts = fen.trim().split(/\s+/);
    if (parts.length < 1) return false; // Must have at least piece placement

    const [piecePlacement, activeColor, castling, enPassant, halfMove, fullMove] = parts;

    // 1. Piece Placement
    const ranks = piecePlacement.split('/');
    if (ranks.length !== 8) return false;
    for (const rank of ranks) {
      let count = 0;
      for (const char of rank) {
        if (/[1-8]/.test(char)) {
          count += parseInt(char, 10);
        } else if (/[prnbqkPRNBQK]/.test(char)) {
          count++;
        } else {
          return false; // Invalid character
        }
      }
      if (count !== 8) return false; // Each rank must sum to 8
    }

    // These fields are optional for our use case, but if they exist, they should be valid.
    // 2. Active Color
    if (activeColor && !/^[wb]$/.test(activeColor)) return false;

    // 3. Castling Availability
    if (castling && !/^(-|K?Q?k?q?)$/.test(castling)) return false;

    // 4. En Passant Target Square
    if (enPassant && !/^(-|[a-h][36])$/.test(enPassant)) return false;

    // 5. Halfmove Clock
    if (halfMove && (!/^\d+$/.test(halfMove) || parseInt(halfMove, 10) < 0)) return false;
    
    // 6. Fullmove Number
    if (fullMove && (!/^\d+$/.test(fullMove) || parseInt(fullMove, 10) <= 0)) return false;


    return true;
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
  
  const validation = fenSchema.safeParse(fenInput);

  if (!validation.success) {
      return { ...currentState, error: 'Invalid FEN string. Please check the format and ensure all 6 fields are present.' };
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
      fen: fenInput,
      key: Math.random(),
    };
  } catch (e) {
    console.error(e);
    const errorMessage = e instanceof Error ? e.message : 'An unknown error occurred.';
    return { ...currentState, key: Math.random(), error: `Error processing FEN: ${errorMessage}` };
  }
}
