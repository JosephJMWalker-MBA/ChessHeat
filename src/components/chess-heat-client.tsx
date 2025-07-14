'use client';

import { useActionState, useEffect, useState } from 'react';
import { getChessHeatmap, type ChessHeatState } from '../app/actions';
import { Chessboard } from '@/components/chessboard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

export function ChessHeatClient({ initialState }: { initialState: ChessHeatState }) {
  const [state, formAction, isPending] = useActionState(getChessHeatmap, initialState);
  const [currentFen, setCurrentFen] = useState(initialState.fen);

  useEffect(() => {
    if (state.fen) {
      setCurrentFen(state.fen);
    }
  }, [state.fen]);
  
  return (
    <main className="min-h-screen bg-background text-foreground p-4 sm:p-8">
      <div className="max-w-4xl mx-auto flex flex-col items-center gap-8">
        <header className="text-center">
          <h1 className="text-4xl sm:text-5xl font-headline font-bold text-primary">ChessHeat</h1>
          <p className="mt-2 text-lg text-muted-foreground">Visualize square control and tactical pressure on the chessboard.</p>
        </header>

        <div className="w-full max-w-2xl">
          <Chessboard key={state.key} board={state.board} influenceMatrix={state.influenceMatrix} />
        </div>

        <Card className="w-full max-w-2xl">
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
            {state.error && (
              <Alert variant="destructive" className="mt-4">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{state.error}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
        
        <Card className="w-full max-w-2xl">
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
    </main>
  );
}
