
'use client';

import { Piece } from './chess-pieces';
import type { Board, InfluenceData, SquareDetails } from '@/lib/chess-logic';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { SelectedSquare } from './chess-heat-client';

interface ChessboardProps {
  board: Board;
  influenceData: InfluenceData;
  className?: string;
  orientation?: 'w' | 'b';
  onSquareSelect: (r: number, c: number) => void;
  selectedSquare: SelectedSquare;
}

function getBackgroundColor(value: number, absoluteMax: number): string {
  if (absoluteMax === 0) {
    return 'transparent';
  }

  const intensity = Math.min(1, Math.sqrt(Math.abs(value) / absoluteMax));
  
  if (value > 0) {
    // White's influence: Primary color (blue)
    return `hsla(207, 44%, 49%, ${intensity * 0.75})`;
  } else if (value < 0) {
    // Black's influence: A contrasting orange
    return `hsla(30, 90%, 50%, ${intensity * 0.75})`;
  }

  return 'transparent';
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

function getBoardView(board: Board, orientation: 'w' | 'b') {
  if (orientation === 'w') {
    return board;
  }
  // For black's orientation, we need to reverse rows and columns
  return board.map(row => [...row].reverse()).reverse();
}

function getInfluenceDataView(influenceData: InfluenceData, orientation: 'w' | 'b') {
    if (orientation === 'w') {
        return influenceData;
    }
    const { netInfluence, detailedInfluence } = influenceData;
    const reversedNet = netInfluence.map(row => [...row].reverse()).reverse();
    const reversedDetailed = detailedInfluence.map(row => [...row].reverse()).reverse();
    return { netInfluence: reversedNet, detailedInfluence: reversedDetailed };
}


export function Chessboard({ board, influenceData, className, orientation = 'w', onSquareSelect, selectedSquare }: ChessboardProps) {
  const allValues = influenceData.netInfluence.flat();
  const absoluteMax = Math.max(...allValues.map(v => Math.abs(v)), 1);

  const whiteFiles = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  const whiteRanks = ['8', '7', '6', '5', '4', '3', '2', '1'];
  
  const files = orientation === 'w' ? whiteFiles : [...whiteFiles].reverse();
  const ranks = orientation === 'w' ? whiteRanks : [...whiteRanks].reverse();

  const boardView = getBoardView(board, orientation);
  const influenceDataView = getInfluenceDataView(influenceData, orientation);

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
            {boardView.map((row, r) => row.map((piece, c) => {
            const isLightSquare = (r + c) % 2 !== 0;
            const influence = influenceDataView.netInfluence[r][c] || 0;
            const squareDetails = influenceDataView.detailedInfluence[r][c];
            const heatColor = getBackgroundColor(influence, absoluteMax);
            
            const whiteAttackers = squareDetails.attackers.filter(p => p.piece[0] === 'w');
            const blackAttackers = squareDetails.attackers.filter(p => p.piece[0] === 'b');
            const isSelected = selectedSquare?.r === r && selectedSquare?.c === c;

            return (
              <Tooltip key={`${r}-${c}`} delayDuration={100}>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={() => onSquareSelect(r, c)}
                    onFocus={() => onSquareSelect(r, c)}
                    aria-label={`Square ${files[c]}${ranks[r]}`}
                    className={cn(
                      'relative flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 z-10',
                      isLightSquare ? 'bg-card' : 'bg-muted/60'
                    )}
                  >
                    <div className="absolute inset-0 transition-colors duration-500" style={{ backgroundColor: heatColor }} />
                    {isSelected && <div className="absolute inset-0 ring-2 ring-accent z-20" />}
                    <Piece piece={piece} />
                    {influence !== 0 && (
                        <span className="absolute bottom-0 right-1 text-[10px] font-bold text-white/90 mix-blend-difference pointer-events-none">
                            {influence > 0 ? `+${influence.toFixed(0)}` : influence.toFixed(0)}
                        </span>
                    )}
                  </button>
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
