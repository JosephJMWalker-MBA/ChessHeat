'use client';

import { Piece } from './chess-pieces';
import type { Board, InfluenceMatrix } from '@/lib/chess-logic';
import { cn } from '@/lib/utils';

interface ChessboardProps {
  board: Board;
  influenceMatrix: InfluenceMatrix;
  className?: string;
}

function getBackgroundColor(value: number, min: number, max: number): string {
  if (value === 0) {
    return 'transparent';
  }
  
  if (value > 0) {
    // Primary color: Saturated blue (hsl(207, 44%, 49%))
    const intensity = Math.min(1, value / (max || 1));
    return `hsla(207, 44%, 49%, ${intensity * 0.65})`;
  } else {
    // Red for negative influence
    const intensity = Math.min(1, Math.abs(value) / (Math.abs(min) || 1));
    return `hsla(0, 70%, 50%, ${intensity * 0.65})`;
  }
}

export function Chessboard({ board, influenceMatrix, className }: ChessboardProps) {
  const allValues = influenceMatrix.flat();
  const maxValue = Math.max(...allValues.filter(v => v > 0), 1);
  const minValue = Math.min(...allValues.filter(v => v < 0), -1);

  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  const ranks = ['8', '7', '6', '5', '4', '3', '2', '1'];

  return (
    <div className={cn("grid grid-cols-8 aspect-square shadow-lg border border-border relative", className)}>
        {ranks.map((rank, i) => (
            <div key={rank} className="absolute -left-5 w-4 h-[12.5%] text-xs font-medium text-muted-foreground flex items-center justify-center" style={{top: `${i * 12.5}%`}}>
                {rank}
            </div>
        ))}
        {files.map((file, i) => (
            <div key={file} className="absolute -bottom-5 h-4 w-[12.5%] text-xs font-medium text-muted-foreground flex items-center justify-center" style={{left: `${i * 12.5}%`}}>
                {file}
            </div>
        ))}
        
      {board.map((row, r) => row.map((piece, c) => {
        const isLightSquare = (r + c) % 2 !== 0;
        const influence = influenceMatrix[r][c] || 0;
        const heatColor = getBackgroundColor(influence, minValue, maxValue);
        return (
          <div
            key={`${r}-${c}`}
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
        )
      }))}
    </div>
  )
}
