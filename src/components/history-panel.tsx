
'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from './ui/separator';
import { SquareDetailsDisplay } from './square-details-display';
import type { SquareDetails } from '@/lib/chess-logic';
import type { SelectedSquare } from './chess-heat-client';

interface HistoryPanelProps {
    insights: string;
    isPending: boolean;
    squareDetails: SquareDetails | null;
    selectedSquare: SelectedSquare;
    orientation: 'w' | 'b';
}

export function HistoryPanel({ insights, isPending, squareDetails, selectedSquare, orientation }: HistoryPanelProps) {
  return (
    <div className="flex flex-col gap-4 p-4 h-full">
        <div className="flex-shrink-0">
            <h2 className="font-headline text-xl font-bold text-sidebar-foreground">Analysis</h2>
            <p className="text-sm text-muted-foreground">Tactical insights and details.</p>
        </div>
        
        <div className="flex-grow overflow-y-auto space-y-6 pr-2">
            <section>
                <h3 className="font-headline text-lg font-semibold text-sidebar-foreground mb-2">AI Insights</h3>
                <div className="text-sm text-muted-foreground mb-4">Highlights of squares with complex tactical interdependencies.</div>
                {isPending ? (
                <div className="space-y-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                </div>
                ) : (
                <p className="text-sm whitespace-pre-wrap leading-relaxed text-sidebar-foreground/90">{insights}</p>
                )}
            </section>
            
            <Separator className="bg-sidebar-border" />
            
            <section>
                <SquareDetailsDisplay details={squareDetails} orientation={orientation} selectedSquare={selectedSquare} />
            </section>
        </div>
    </div>
  );
}
