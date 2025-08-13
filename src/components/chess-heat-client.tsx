
'use client';

import { useActionState, useEffect, useState, useTransition } from 'react';
import { getChessHeatmap, type ChessHeatState } from '../app/actions';
import { Chessboard } from '@/components/chessboard';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { SwitchCamera, Trash2 } from 'lucide-react';
import { SquareDetailsDisplay } from './square-details-display';
import type { SquareDetails, Board, Piece as PieceType } from '@/lib/chess-logic';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { Piece } from './chess-pieces';
import { PieceBin } from './piece-bin';
import { buildFen } from '@/lib/chess-logic';

export type SelectedSquare = { r: number; c: number } | null;

const pieceSet: PieceType[] = ['wK', 'wQ', 'wR', 'wB', 'wN', 'wP', 'bK', 'bQ', 'bR', 'bB', 'bN', 'bP'];

export function ChessHeatClient({ initialState }: { initialState: ChessHeatState }) {
  const { toast } = useToast();
  const [state, formAction, isPending] = useActionState(getChessHeatmap, initialState);
  const [orientation, setOrientation] = useState<'w' | 'b'>('w');
  const [selectedSquare, setSelectedSquare] = useState<SelectedSquare>(null);
  const [isClient, setIsClient] = useState(false);
  const [isAnalyzing, startTransition] = useTransition();

  // We need to keep a separate board state for the interactive editor
  const [editorBoard, setEditorBoard] = useState<Board>(initialState.board);
  const [currentFen, setCurrentFen] = useState(initialState.fen);

  useEffect(() => {
    setIsClient(true);
  }, []);
  
  useEffect(() => {
    // This effect synchronizes the editor's board state with the server's state
    // when the server responds with a new analysis.
    setEditorBoard(state.board);
    setCurrentFen(state.fen);
  }, [state.key]); // Use the key to detect when a new analysis is complete


  useEffect(() => {
    if (state.error) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: state.error,
      });
    }
    // Reset selected square on new analysis
    setSelectedSquare(null);
  }, [state, toast]);
  
  const getSquareDetails = (): SquareDetails | null => {
    if (!selectedSquare) return null;
    
    const {r, c} = selectedSquare;
    const canonicalR = orientation === 'w' ? r : 7 - r;
    const canonicalC = orientation === 'w' ? c : 7 - c;
    
    return state.influenceData.detailedInfluence[canonicalR][canonicalC];
  }

  const handleSquareSelect = (r: number, c: number) => {
    if (selectedSquare && selectedSquare.r === r && selectedSquare.c === c) {
      setSelectedSquare(null);
    } else {
      setSelectedSquare({ r, c });
    }
  };

  const handlePieceDrop = (piece: PieceType, toR: number, toC: number, from: {r: number, c: number} | null) => {
    const newBoard = editorBoard.map(row => [...row]);
    
    // If piece came from another square, clear the old square
    if (from) {
      newBoard[from.r][from.c] = null;
    }

    newBoard[toR][toC] = piece;
    setEditorBoard(newBoard);

    // Update FEN and trigger analysis
    const newFen = buildFen(newBoard, 'w', '-', '-', 0, 1);
    setCurrentFen(newFen);

    startTransition(() => {
      const formData = new FormData();
      formData.append('fen', newFen);
      formAction(formData);
    });
  };

  const handleClearBoard = () => {
    const newBoard = Array(8).fill(null).map(() => Array(8).fill(null));
    setEditorBoard(newBoard);
    const newFen = '8/8/8/8/8/8/8/8 w - - 0 1';
    setCurrentFen(newFen);
    startTransition(() => {
        const formData = new FormData();
        formData.append('fen', newFen);
        formAction(formData);
    });
  }

  return (
    <DndProvider backend={HTML5Backend}>
      <main className="min-h-screen bg-background text-foreground p-4 sm:p-8">
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-start gap-8">
          <div className="w-full lg:w-auto lg:flex-shrink-0 flex flex-col items-center gap-8">
            <header className="text-center lg:hidden">
              <h1 className="text-4xl sm:text-5xl font-headline font-bold text-primary">ChessHeat</h1>
              <p className="mt-2 text-lg text-muted-foreground">Interactive board editor & influence visualizer.</p>
            </header>

            <div className="w-full max-w-2xl lg:max-w-[60vh] relative">
              {isClient ? (
                <Chessboard
                  key={`${state.key}-${orientation}`}
                  board={editorBoard}
                  influenceData={state.influenceData}
                  orientation={orientation}
                  onSquareSelect={handleSquareSelect}
                  selectedSquare={selectedSquare}
                  onPieceDrop={handlePieceDrop}
                />
              ) : <Skeleton className="aspect-square w-full" />}
              <Button
                variant="outline"
                size="icon"
                onClick={() => setOrientation(o => (o === 'w' ? 'b' : 'w'))}
                aria-label="Flip board"
                className="absolute top-2 right-2 z-20 bg-card/80 hover:bg-card"
              >
                <SwitchCamera className="h-5 w-5" />
              </Button>
            </div>
            
            <Card className="w-full max-w-2xl lg:max-w-[60vh]">
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle className="font-headline">Piece Box</CardTitle>
                        <CardDescription>Drag pieces to the board.</CardDescription>
                    </div>
                    <Button variant="outline" size="icon" onClick={handleClearBoard} aria-label="Clear Board">
                        <Trash2 className="h-5 w-5"/>
                    </Button>
                </CardHeader>
                <CardContent className="grid grid-cols-6 gap-2">
                    {pieceSet.map(p => <PieceBin key={p} piece={p} />)}
                </CardContent>
            </Card>

          </div>

          <div className="w-full flex-grow flex flex-col gap-8">
              <header className="text-left hidden lg:block">
                <h1 className="text-5xl font-headline font-bold text-primary">ChessHeat</h1>
                <p className="mt-2 text-lg text-muted-foreground">Interactive board editor & influence visualizer.</p>
              </header>
              
              <SquareDetailsDisplay details={getSquareDetails()} orientation={orientation} selectedSquare={selectedSquare} />

              <Card className="w-full">
                  <CardHeader>
                      <CardTitle className="font-headline">AI Insights</CardTitle>
                      <CardDescription>Highlights of squares with complex tactical interdependencies.</CardDescription>
                  </CardHeader>
                  <CardContent>
                      {isPending || isAnalyzing ? (
                      <div className="space-y-2">
                          <Skeleton className="h-4 w-full" />
                          <Skeleton className="h-4 w-full" />
                          <Skeleton className="h-4 w-3/4" />
                      </div>
                      ) : (
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">{state.insights}</p>
                      )}
                  </CardContent>
              </Card>

              <Card className="w-full">
                  <CardHeader>
                      <CardTitle className="font-headline">FEN</CardTitle>
                      <CardDescription>The Forsyth-Edwards Notation for the current position.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm font-mono bg-muted p-2 rounded-md break-all">{currentFen}</p>
                  </CardContent>
              </Card>

          </div>
        </div>
      </main>
    </DndProvider>
  );
}
