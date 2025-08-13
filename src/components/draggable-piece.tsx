// src/components/draggable-piece.tsx
import { useDrag } from 'react-dnd';
import { Piece } from './chess-pieces';
import type { Piece as PieceType } from '@/lib/chess-logic';
import { cn } from '@/lib/utils';

interface DraggablePieceProps {
  piece: PieceType;
  r: number;
  c: number;
}

export function DraggablePiece({ piece, r, c }: DraggablePieceProps) {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'piece',
    item: { piece, from: {r, c} },
    collect: (monitor) => ({
      isDragging: !!monitor.isDragging(),
    }),
  }), [piece, r, c]);

  return (
    <div
      ref={drag}
      className={cn(
        "w-full h-full cursor-grab",
        isDragging ? 'opacity-50' : 'opacity-100'
      )}
    >
      <Piece piece={piece} />
    </div>
  );
}
