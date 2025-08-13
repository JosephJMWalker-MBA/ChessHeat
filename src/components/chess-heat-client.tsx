
'use client';

import { useActionState, useEffect, useState } from 'react';
import { getChessHeatmap, type ChessHeatState } from '../app/actions';
import { Chessboard } from '@/components/chessboard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { SwitchCamera } from 'lucide-react';
import { SquareDetailsDisplay } from './square-details-display';
import type { SquareDetails } from '@/lib/chess-logic';

export type SelectedSquare = { r: number; c: number } | null;

export function ChessHeatClient({ initialState }: { initialState: ChessHeatState }) {
  const { toast } = useToast();
  const [state, formAction, isPending] = useActionState(getChessHeatmap, initialState);
  const [currentFen, setCurrentFen] = useState(initialState.fen);
  const [orientation, setOrientation] = useState<'w' | 'b'>('w');
  const [selectedSquare, setSelectedSquare] = useState<SelectedSquare>(null);

  useEffect(() => {
    if (state.fen) {
      setCurrentFen(state.fen);
    }
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

    if (orientation === 'w') {
      return state.influenceData.detailedInfluence[r][c];
    }
    
    // Adjust for black's orientation
    const reversedR = 7 - r;
    const reversedC = 7 - c;
    return state.influenceData.detailedInfluence[reversedR][reversedC];
  }

  const handleSquareSelect = (r: number, c: number) => {
    if (selectedSquare && selectedSquare.r === r && selectedSquare.c === c) {
      setSelectedSquare(null); // Deselect if clicking the same square
    } else {
      setSelectedSquare({ r, c });
    }
  };

  return (
    <main className="min-h-screen bg-background text-foreground p-4 sm:p-8">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-start gap-8">
        <div className="w-full lg:w-auto lg:flex-shrink-0 flex flex-col items-center gap-8">
          <header className="text-center lg:hidden">
            <h1 className="text-4xl sm:text-5xl font-headline font-bold text-primary">ChessHeat</h1>
            <p className="mt-2 text-lg text-muted-foreground">Visualize square control and tactical pressure.</p>
          </header>

          <div className="w-full max-w-2xl lg:max-w-[60vh] relative">
            <Chessboard
              key={`${state.key}-${orientation}`}
              board={state.board}
              influenceData={state.influenceData}
              orientation={orientation}
              onSquareSelect={handleSquareSelect}
              selectedSquare={selectedSquare}
            />
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
            <CardHeader>
              <CardTitle className="font-headline">Analyze a Position</CardTitle>
              <CardDescription>Enter a FEN string to generate a heatmap and AI-powered insights.</CardDescription>
            </CardHeader>
            <CardContent>
              <form action={formAction} className="flex flex-col sm:flex-row gap-2">
                <Input
                  name="fen"
                  placeholder="e.g., rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
                  value={currentFen}
                  onChange={(e) => setCurrentFen(e.target.value)}
                  className="font-mono flex-grow"
                />
                <Button type="submit" disabled={isPending} className="w-full sm:w-auto bg-primary hover:bg-primary/90">
                  {isPending ? 'Analyzing...' : 'Visualize'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        <div className="w-full flex-grow flex flex-col gap-8">
            <header className="text-left hidden lg:block">
              <h1 className="text-5xl font-headline font-bold text-primary">ChessHeat</h1>
              <p className="mt-2 text-lg text-muted-foreground">Visualize square control and tactical pressure on the chessboard.</p>
            </header>
            
            <SquareDetailsDisplay details={getSquareDetails()} orientation={orientation} selectedSquare={selectedSquare} />

            <Card className="w-full">
                <CardHeader>
                    <CardTitle className="font-headline">AI Insights</CardTitle>
                    <CardDescription>Highlights of squares with complex tactical interdependencies.</CardDescription>
                </CardHeader>
                <CardContent>
                    {isPending ? (
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
        </div>
      </div>
    </main>
  );
}
