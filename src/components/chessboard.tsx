
'use client';

import { Piece } from './chess-pieces';
import type { Board, InfluenceData } from '@/lib/chess-logic';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface ChessboardProps {
  board: Board;
  influenceData: InfluenceData;
  className?: string;
}

function getBackgroundColor(value: number, absoluteMax: number): string {
  if (value === 0 || absoluteMax === 0) {
    return 'transparent';
  }

  const intensity = Math.min(1, Math.sqrt(Math.abs(value) / absoluteMax));
  
  if (value > 0) {
    // White's influence: Primary color (blue)
    return `hsla(207, 44%, 49%, ${intensity * 0.75})`;
  } else {
    // Black's influence: A contrasting orange
    return `hsla(30, 90%, 50%, ${intensity * 0.75})`;
  }
}


const PIECE_NAMES: Record<string, string> = {
  K: 'King', Q: 'Queen', R: 'Rook', B: 'Bishop', N: 'Knight', P: 'Pawn'
}

function PieceList({ title, pieces }: { title: string, pieces: { piece: string }[] }) {
  if (pieces.length === 0) return null;
  return (
    <div>
      <h4 className="font-bold text-sm">{title}</h4>
      <ul className="text-xs list-disc pl-4">
        {pieces.map(({ piece }, index) => {
          const color = piece[0] === 'w' ? 'White' : 'Black';
          const type = PIECE_NAMES[piece[1]] || 'Piece';
          return <li key={index}>{color} {type}</li>;
        })}
      </ul>
    </div>
  )
}

export function Chessboard({ board, influenceData, className }: ChessboardProps) {
  const allValues = influenceData.netInfluence.flat();
  const absoluteMax = Math.max(...allValues.map(v => Math.abs(v)), 1);

  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  const ranks = ['8', '7', '6', '5', '4', '3', '2', '1'];

  return (
    <TooltipProvider>
      <div className={cn("aspect-square shadow-lg border border-border relative", className)}>
        <div className="absolute -left-5 top-0 h-full w-4 flex flex-col">
            {ranks.map((rank) => (
                <div key={rank} className="flex-1 text-xs font-medium text-muted-foreground flex items-center justify-center">
                    {rank}
                </div>
            ))}
        </div>
        <div className="absolute -bottom-5 left-0 w-full h-4 flex">
            {files.map((file) => (
                <div key={file} className="flex-1 text-xs font-medium text-muted-foreground flex items-center justify-center">
                    {file}
                </div>
            ))}
        </div>
          
        <div className="grid grid-cols-8 grid-rows-8 h-full w-full">
            {board.map((row, r) => row.map((piece, c) => {
            const isLightSquare = (r + c) % 2 !== 0;
            const influence = influenceData.netInfluence[r][c] || 0;
            const squareDetails = influenceData.detailedInfluence[r][c];
            const heatColor = getBackgroundColor(influence, absoluteMax);
            
            const whiteAttackers = squareDetails.attackers.filter(p => p.piece[0] === 'w');
            const blackAttackers = squareDetails.attackers.filter(p => p.piece[0] === 'b');

            return (
                <Tooltip key={`${r}-${c}`} delayDuration={100}>
                <TooltipTrigger asChild>
                    <div
                    className={cn('relative flex items-center justify-center', isLightSquare ? 'bg-card' : 'bg-muted/60')}
                    >
                    <div className="absolute inset-0 transition-colors duration-500" style={{ backgroundColor: heatColor }} />
                    <Piece piece={piece} />
                    {influence !== 0 && (
                        <span className="absolute bottom-0 right-1 text-[10px] font-bold text-white/90 mix-blend-difference pointer-events-none">
                            {influence > 0 ? `+${influence.toFixed(0)}` : influence.toFixed(0)}
                        </span>
                    )}
                    </div>
                </TooltipTrigger>
                {(squareDetails.attackers.length > 0 || squareDetails.defenders.length > 0) && (
                    <TooltipContent>
                        <div className="p-1 space-y-2">
                        <PieceList title="Attackers (White)" pieces={whiteAttackers} />
                        <PieceList title="Attackers (Black)" pieces={blackAttackers} />
                        <PieceList title="Defenders" pieces={squareDetails.defenders} />
                        </div>
                    </TooltipContent>
                )}
                </Tooltip>
            )
            }))}
        </div>
      </div>
    </TooltipProvider>
  )
}
