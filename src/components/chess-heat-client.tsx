
'use client';

import { useActionState, useEffect, useState, useTransition } from 'react';
import { getChessHeatmap, type ChessHeatState } from '../app/actions';
import { Chessboard } from '@/components/chessboard';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { SwitchCamera, Trash2 } from 'lucide-react';
import type { SquareDetails, Board, Piece as PieceType } from '@/lib/chess-logic';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { PieceBin } from './piece-bin';
import { buildFen } from '@/lib/chess-logic';
import { HistoryPanel } from './history-panel';
import { Sidebar, SidebarContent, SidebarInset, SidebarProvider, SidebarTrigger } from './ui/sidebar';

export type SelectedSquare = { r: number; c: number } | null;

const pieceSet: PieceType[] = ['wK', 'wQ', 'wR', 'wB', 'wN', 'wP', 'bK', 'bQ', 'bR', 'bB', 'bN', 'bP'];

export function ChessHeatClient({ initialState }: { initialState: ChessHeatState }) {
  const { toast } = useToast();
  const [state, formAction, isPending] = useActionState(getChessHeatmap, initialState);
  const [orientation, setOrientation] = useState<'w' | 'b'>('w');
  const [selectedSquare, setSelectedSquare] = useState<SelectedSquare>(null);
  const [isClient, setIsClient] = useState(false);
  const [isAnalyzing, startTransition] = useTransition();

  const [editorBoard, setEditorBoard] = useState<Board>(initialState.board);
  const [currentFen, setCurrentFen] = useState(initialState.fen);

  useEffect(() => {
    setIsClient(true);
  }, []);
  
  useEffect(() => {
    setEditorBoard(state.board);
    setCurrentFen(state.fen);
  }, [state.key]); 


  useEffect(() => {
    if (state.error) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: state.error,
      });
    }
    setSelectedSquare(null);
  }, [state, toast]);
  
  const getSquareDetails = (): SquareDetails | null => {
    if (!selectedSquare) return null;
    
    const {r, c} = selectedSquare;
    const canonicalR = orientation === 'w' ? r : 7 - r;
    const canonicalC = orientation === 'w' ? c : 7 - c;
    
    if (state.influenceData.detailedInfluence[canonicalR] && state.influenceData.detailedInfluence[canonicalR][canonicalC]) {
      return state.influenceData.detailedInfluence[canonicalR][canonicalC];
    }
    return null;
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
    
    if (from) {
      newBoard[from.r][from.c] = null;
    }

    newBoard[toR][toC] = piece;
    setEditorBoard(newBoard);

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
      <SidebarProvider defaultOpen={true}>
        <div className="min-h-screen bg-background text-foreground">
          <SidebarInset className="p-4 sm:p-6 lg:p-8">
            <main className="flex-1 flex flex-col gap-6">
              <header className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <h1 className="text-3xl sm:text-4xl font-headline font-bold text-primary">ChessHeat</h1>
                  <p className="mt-1 text-md text-muted-foreground hidden md:block">Interactive board editor & influence visualizer.</p>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="icon"
                        onClick={() => setOrientation(o => (o === 'w' ? 'b' : 'w'))}
                        aria-label="Flip board"
                        className="bg-card/80 hover:bg-card"
                    >
                        <SwitchCamera className="h-5 w-5" />
                    </Button>
                    <SidebarTrigger />
                </div>
              </header>

              <div className="w-full flex-1 flex flex-col items-center justify-center gap-6">
                  <div className="w-full max-w-4xl mx-auto">
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
                  </div>

                  <Card className="w-full max-w-2xl">
                      <CardHeader className="flex flex-row items-center justify-between py-3">
                          <div>
                              <CardTitle className="font-headline text-2xl">Piece Box</CardTitle>
                              <CardDescription>Drag pieces to the board.</CardDescription>
                          </div>
                          <Button variant="outline" size="icon" onClick={handleClearBoard} aria-label="Clear Board">
                              <Trash2 className="h-5 w-5"/>
                          </Button>
                      </CardHeader>
                      <CardContent className="grid grid-cols-6 gap-2 p-4">
                          {pieceSet.map(p => <PieceBin key={p} piece={p} />)}
                      </CardContent>
                  </Card>
              </div>

            </main>
          </SidebarInset>

          <Sidebar side="right" collapsible="icon">
              <SidebarContent>
                  <HistoryPanel
                      fen={currentFen}
                      insights={state.insights}
                      isPending={isPending || isAnalyzing}
                      squareDetails={getSquareDetails()}
                      selectedSquare={selectedSquare}
                      orientation={orientation}
                  />
              </SidebarContent>
          </Sidebar>
        </div>
      </SidebarProvider>
    </DndProvider>
  );
}
