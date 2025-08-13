// src/components/piece-bin.tsx
import { useDrag } from 'react-dnd';
import { Piece } from './chess-pieces';
import type { Piece as PieceType } from '@/lib/chess-logic';
import { cn } from '@/lib/utils';

interface PieceBinProps {
  piece: PieceType;
}

export function PieceBin({ piece }: PieceBinProps) {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'piece',
    item: { piece, from: null }, // from is null because it's from the bin
    collect: (monitor) => ({
      isDragging: !!monitor.isDragging(),
    }),
  }), [piece]);

  return (
    <div
      ref={drag}
      className={cn(
        "w-full h-full aspect-square cursor-grab rounded-md bg-muted/50 p-1 flex items-center justify-center",
        isDragging ? 'opacity-50' : 'opacity-100'
      )}
    >
      <Piece piece={piece} />
    </div>
  );
}
