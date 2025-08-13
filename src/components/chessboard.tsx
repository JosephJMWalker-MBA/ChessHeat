
'use client';

import { Piece } from './chess-pieces';
import type { Board, InfluenceData, Piece as PieceType } from '@/lib/chess-logic';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { SelectedSquare } from './chess-heat-client';
import { useDrop } from 'react-dnd';
import { DraggablePiece } from './draggable-piece';

interface ChessboardProps {
  board: Board;
  influenceData: InfluenceData;
  className?: string;
  orientation?: 'w' | 'b';
  onSquareSelect: (r: number, c: number) => void;
  selectedSquare: SelectedSquare;
  onPieceDrop: (piece: PieceType, r: number, c: number, from: {r: number, c: number} | null) => void;
}

function getBackgroundColor(value: number, absoluteMax: number): string {
  if (absoluteMax === 0 || value === 0) {
    return 'transparent';
  }

  const intensity = Math.min(1, Math.sqrt(Math.abs(value) / absoluteMax));
  
  if (value > 0) {
    // White's influence: Primary color (blue)
    return `hsla(207, 90%, 54%, ${intensity * 0.6})`;
  } else {
    // Black's influence: A contrasting red
    return `hsla(0, 72%, 51%, ${intensity * 0.6})`;
  }
}

// Helper to get a view of the board based on orientation
function getBoardView(board: Board, orientation: 'w' | 'b') {
  if (orientation === 'w') {
    return board;
  }
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


function Square({ r, c, children, isLightSquare, onDrop }: { r: number, c: number, children: React.ReactNode, isLightSquare: boolean, onDrop: (item: { type: string, piece: PieceType, from: { r: number; c: number } | null }) => void }) {
  const [{ isOver, canDrop }, drop] = useDrop(() => ({
    accept: 'piece',
    drop: (item: { type: string, piece: PieceType, from: {r: number, c: number} | null }) => onDrop(item),
    collect: (monitor) => ({
      isOver: !!monitor.isOver(),
      canDrop: !!monitor.canDrop(),
    }),
  }), [r, c]);

  return (
    <div ref={drop} className={cn('relative h-full w-full', isLightSquare ? 'bg-card' : 'bg-muted/60')}>
      {children}
      {isOver && canDrop && <div className="absolute inset-0 bg-yellow-400/50" />}
    </div>
  )
}

export function Chessboard({ board, influenceData, className, orientation = 'w', onSquareSelect, selectedSquare, onPieceDrop }: ChessboardProps) {
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
      <div className={cn("aspect-square w-full shadow-lg border border-border relative", className)}>
        {/* Rank labels */}
        <div className="absolute -left-5 top-0 h-full w-4 flex flex-col">
            {ranks.map((rank) => (
                <div key={rank} className="flex-1 text-xs font-medium text-muted-foreground flex items-center justify-center">
                    {rank}
                </div>
            ))}
        </div>
        {/* File labels */}
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
              const heatColor = getBackgroundColor(influence, absoluteMax);
              const isSelected = selectedSquare?.r === r && selectedSquare?.c === c;
              
              // Get canonical coordinates for piece drop handling
              const canonicalR = orientation === 'w' ? r : 7 - r;
              const canonicalC = orientation === 'w' ? c : 7 - c;

              return (
                <Square 
                  key={`${r}-${c}`}
                  r={r} 
                  c={c} 
                  isLightSquare={isLightSquare} 
                  onDrop={(item) => onPieceDrop(item.piece, canonicalR, canonicalC, item.from)}
                >
                  <Tooltip delayDuration={300}>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        onClick={() => onSquareSelect(r, c)}
                        onFocus={() => onSquareSelect(r, c)}
                        aria-label={`Square ${files[c]}${ranks[r]}`}
                        className={cn(
                          'relative flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 z-10 w-full h-full'
                        )}
                      >
                        <div className="absolute inset-0 transition-colors duration-500 pointer-events-none" style={{ backgroundColor: heatColor }} />
                        {isSelected && <div className="absolute inset-0 ring-2 ring-accent z-20 pointer-events-none" />}
                        {piece ? (
                          <DraggablePiece piece={piece} r={canonicalR} c={canonicalC} />
                        ) : null}

                        {influence !== 0 && (
                            <span className="absolute bottom-0 right-1 text-[10px] font-bold text-white/90 mix-blend-difference pointer-events-none">
                                {influence > 0 ? `+${influence.toFixed(0)}` : influence.toFixed(0)}
                            </span>
                        )}
                      </button>
                    </TooltipTrigger>
                  </Tooltip>
                </Square>
              )
            }))}
        </div>
      </div>
    </TooltipProvider>
  )
}
