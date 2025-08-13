
export type Piece = string; // e.g., 'wP', 'bN'
export type Board = (Piece | null)[][];
export type InfluenceMatrix = number[][];

export interface SquareDetails {
    attackers: { piece: Piece; from: { r: number; c: number } }[];
    defenders: { piece: Piece; from: { r: number; c: number } }[];
}

export type DetailedInfluenceMatrix = SquareDetails[][];

export interface InfluenceData {
    netInfluence: InfluenceMatrix;
    detailedInfluence: DetailedInfluenceMatrix;
}


const PIECE_VALUES: { [key: string]: number } = {
  p: 1, n: 3, b: 3, r: 5, q: 9, k: 0,
};

// Parses the piece placement part of a FEN string.
export function parseFEN(fen: string): Board {
  const board: Board = Array(8).fill(null).map(() => Array(8).fill(null));
  const [piecePlacement] = fen.split(' ');
  const ranks = piecePlacement.split('/');

  if (ranks.length !== 8) throw new Error('Invalid FEN: Must have 8 ranks.');

  for (let r = 0; r < 8; r++) {
    let fileIndex = 0;
    for (const char of ranks[r]) {
      if (fileIndex >= 8) break;
      if (isNaN(parseInt(char))) {
        const color = char === char.toUpperCase() ? 'w' : 'b';
        board[r][fileIndex] = `${color}${char.toUpperCase()}`;
        fileIndex++;
      } else {
        fileIndex += parseInt(char);
      }
    }
  }
  return board;
}


function getAttackedSquares(piece: Piece, r: number, c: number, board: Board): {r: number, c: number}[] {
    const moves: {r: number, c: number}[] = [];
    const color = piece[0];
    const type = piece[1];

    const is_valid = (r: number, c: number) => r >= 0 && r < 8 && c >= 0 && c < 8;

    const add_line_moves = (dr: number, dc: number) => {
        let cr = r + dr, cc = c + dc;
        while (is_valid(cr, cc)) {
            moves.push({r: cr, c: cc});
            const targetPiece = board[cr][cc];
            // Stop if the square is occupied by any piece. The influence stops here.
            if (targetPiece) {
                break;
            }
            cr += dr;
            cc += dc;
        }
    };
    
    switch (type) {
        case 'P':
            const forward = color === 'w' ? -1 : 1;
            // Pawns only attack diagonally.
            if (is_valid(r + forward, c - 1)) moves.push({r: r + forward, c: c - 1});
            if (is_valid(r + forward, c + 1)) moves.push({r: r + forward, c: c + 1});
            break;
        case 'N':
            const knight_moves = [[-2, -1], [-2, 1], [-1, -2], [-1, 2], [1, -2], [1, 2], [2, -1], [2, 1]];
            knight_moves.forEach(([dr, dc]) => {
                if (is_valid(r + dr, c + dc)) moves.push({r: r + dr, c: c + dc});
            });
            break;
        case 'B':
            add_line_moves(1, 1); add_line_moves(1, -1); add_line_moves(-1, 1); add_line_moves(-1, -1);
            break;
        case 'R':
            add_line_moves(1, 0); add_line_moves(-1, 0); add_line_moves(0, 1); add_line_moves(0, -1);
            break;
        case 'Q':
            add_line_moves(1, 1); add_line_moves(1, -1); add_line_moves(-1, 1); add_line_moves(-1, -1);
            add_line_moves(1, 0); add_line_moves(-1, 0); add_line_moves(0, 1); add_line_moves(0, -1);
            break;
        case 'K':
            const king_moves = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]];
            king_moves.forEach(([dr, dc]) => {
                if (is_valid(r + dr, c + dc)) moves.push({r: r + dr, c: c + dc});
            });
            break;
    }
    return moves;
}

export function calculateInfluence(board: Board): InfluenceData {
  const netInfluence: InfluenceMatrix = Array(8).fill(null).map(() => Array(8).fill(0));
  const detailedInfluence: DetailedInfluenceMatrix = Array(8).fill(null).map(() => 
    Array(8).fill(null).map(() => ({ attackers: [], defenders: [] }))
  );

  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const piece = board[r][c];
      if (!piece) continue;

      const pieceColor = piece[0];
      const pieceType = piece[1].toLowerCase();
      const pieceValue = PIECE_VALUES[pieceType] * (pieceColor === 'w' ? 1 : -1);
      
      const attackedSquares = getAttackedSquares(piece, r, c, board);
      
      for (const { r: ar, c: ac } of attackedSquares) {
        netInfluence[ar][ac] += pieceValue;
        
        const targetPiece = board[ar][ac];
        if (targetPiece && targetPiece[0] === pieceColor) {
             detailedInfluence[ar][ac].defenders.push({ piece, from: {r,c} });
        } else {
             // If the target square is empty or has an enemy piece, it's an attack.
             detailedInfluence[ar][ac].attackers.push({ piece, from: {r,c} });
        }
      }
    }
  }

  return { netInfluence, detailedInfluence };
}
