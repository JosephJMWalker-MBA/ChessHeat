
import { describe, it, expect } from 'vitest';
import { parseFEN, calculateInfluence } from './chess-logic';
import type { Board } from './chess-logic';

describe('parseFEN', () => {
  it('should parse the starting position correctly', () => {
    const fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    const board = parseFEN(fen);
    expect(board[0][0]).toBe('bR');
    expect(board[7][7]).toBe('wR');
    expect(board[1][0]).toBe('bP');
    expect(board[6][0]).toBe('wP');
    expect(board[3][3]).toBe(null);
  });

  it('should throw an error for a FEN with an invalid rank', () => {
    // This rank has 9 files (1+1+1+1+1+1+1+1+1)
    const fen = 'rnbqkbnr/ppppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    expect(() => parseFEN(fen)).toThrow('Invalid FEN: Rank 7 does not have 8 files.');
  });
    
  it('should throw an error for a FEN with too few ranks', () => {
    const fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP w KQkq - 0 1';
    expect(() => parseFEN(fen)).toThrow('Invalid FEN: Must have 8 ranks.');
  });

  it('should correctly parse a complex middlegame position', () => {
    const fen = 'r1b1k2r/pp1n1ppp/1q2p3/2ppP3/3N4/2P5/PP2QPPP/R3KB1R w KQkq - 0 12';
    const board = parseFEN(fen);
    expect(board[0][0]).toBe('bR');
    expect(board[0][4]).toBe('bK');
    expect(board[4][4]).toBe('wP');
    expect(board[5][3]).toBe('wN');
  });
});

describe('calculateInfluence', () => {
  it('should calculate influence correctly for the starting position', () => {
    const board = parseFEN('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    const { netInfluence } = calculateInfluence(board);

    // d3 square is controlled by white pawn on d2, bishop on c1, queen on d1
    // e6 square is controlled by black pawn on e7, bishop on f8, queen on d8
    // White's influence on d3 should be 1(P) + 3(B) + 9(Q) = 13
    // Black's influence on e6 should be -1(p) - 3(b) - 9(q) = -13
    expect(netInfluence[5][3]).toBe(13); // d3 from white's perspective
    expect(netInfluence[2][4]).toBe(-13); // e6 from white's perspective
  });

  it('should show a pinned piece still exerting influence', () => {
    // Rook on e1 is pinned to the king on g1 by a black rook on a1.
    // However, the white rook on e1 should still "attack" e4.
    const board = parseFEN('r3k1r1/8/8/8/8/8/8/4R1K1 w - - 0 1');
    const { netInfluence, detailedInfluence } = calculateInfluence(board);

    // The rook on e1 attacks e4
    expect(detailedInfluence[4][4].attackers.some(a => a.piece === 'wR' && a.from.r === 7 && a.from.c === 4)).toBe(true);
    // Net influence on e4 should be from the white Rook
    expect(netInfluence[4][4]).toBe(5);
  });
  
  it('sliding piece influence should be blocked by other pieces', () => {
    // White rook on a1, white pawn on a2. Rook's influence should stop at a2.
    const board = parseFEN('8/8/8/8/8/8/P7/R7 w - - 0 1');
    const { netInfluence, detailedInfluence } = calculateInfluence(board);

    // a2 is defended by the rook
    expect(detailedInfluence[6][0].defenders.length).toBe(1);
    expect(detailedInfluence[6][0].defenders[0].piece).toBe('wR');
    
    // a3 should have no influence from the rook
    expect(netInfluence[5][0]).toBe(0);
    expect(detailedInfluence[5][0].attackers.length).toBe(0);
  });
  
  it('King influence should be calculated', () => {
    const board = parseFEN('8/8/8/4k3/8/8/8/K7 b - - 0 1');
    const { netInfluence } = calculateInfluence(board);
    // King on e5 influences d4, e4, f4, d5, f5, d6, e6, f6
    expect(netInfluence[4][3]).toBe(-10); // d5
    expect(netInfluence[4][5]).toBe(-10); // f5
    expect(netInfluence[3][4]).toBe(-10); // e6
    expect(netInfluence[5][4]).toBe(-10); // e4
  });

});
