
import type { SquareDetails } from '@/lib/chess-logic';
import type { SelectedSquare } from './chess-heat-client';

const PIECE_NAMES: Record<string, string> = {
  K: 'King', Q: 'Queen', R: 'Rook', B: 'Bishop', N: 'Knight', P: 'Pawn'
};

function PieceList({ title, pieces }: { title: string, pieces: { piece: string, from: {r: number, c: number} }[] }) {
  if (pieces.length === 0) return null;
  
  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  const ranks = ['8', '7', '6', '5', '4', '3', '2', '1'];
  
  return (
    <div>
      <h4 className="font-semibold text-sm text-sidebar-foreground">{title}</h4>
      <ul className="text-sm list-disc pl-5 mt-1 space-y-1 text-muted-foreground">
        {pieces.map(({ piece, from }, index) => {
          const color = piece[0] === 'w' ? 'White' : 'Black';
          const type = PIECE_NAMES[piece[1]] || 'Piece';
          // 'from' coordinates are always canonical (white-oriented)
          const fromSquare = `${files[from.c]}${ranks[from.r]}`;
          return <li key={index}>{color} {type} (from {fromSquare})</li>;
        })}
      </ul>
    </div>
  );
}

// Gets the algebraic notation for a square based on the current view (orientation)
function getSquareName(square: SelectedSquare, orientation: 'w' | 'b'): string {
    if (!square) return '';
    const files = orientation === 'w' ? ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'] : ['h', 'g', 'f', 'e', 'd', 'c', 'b', 'a'];
    const ranks = orientation === 'w' ? ['8', '7', '6', '5', '4', '3', '2', '1'] : ['1', '2', '3', '4', '5', '6', '7', '8'];
    return `${files[square.c]}${ranks[square.r]}`;
}


export function SquareDetailsDisplay({ details, orientation, selectedSquare }: { details: SquareDetails | null, orientation: 'w' | 'b', selectedSquare: SelectedSquare }) {
  const squareName = getSquareName(selectedSquare, orientation).toUpperCase();

  return (
    <div className="w-full">
        <h3 className="font-headline text-lg font-semibold text-sidebar-foreground mb-2">Square Details{squareName && `: ${squareName}`}</h3>
        <div className="text-sm text-muted-foreground mb-4">
            {details ? 'Attackers and defenders for the selected square.' : 'Click on a square on the board to see its tactical details.'}
        </div>
        {details ? (
          <div className="space-y-4">
            <PieceList title="Attackers" pieces={details.attackers} />
            <PieceList title="Defenders" pieces={details.defenders} />
            {details.attackers.length === 0 && details.defenders.length === 0 && (
                <p className="text-sm text-muted-foreground">This square is not currently attacked or defended by any piece.</p>
            )}
          </div>
        ) : (
            <div className="text-center text-muted-foreground py-8">
                <p>No square selected</p>
            </div>
        )}
    </div>
  );
}
