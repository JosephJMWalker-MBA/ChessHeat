// src/ai/flows/generate-insights.ts
'use server';

/**
 * @fileOverview Flow to generate insights about squares with complex tactical interdependencies.
 *
 * - generateInsights - A function that takes the net influence matrix and returns insights about squares with complex tactical interdependencies.
 * - GenerateInsightsInput - The input type for a  generateInsights function.
 * - GenerateInsightsOutput - The return type for the generateInsights function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const GenerateInsightsInputSchema = z.object({
  netInfluenceMatrix: z
    .array(z.array(z.number()))
    .describe('The net influence matrix of the chessboard.'),
  detailedInfluence: z.array(z.array(z.object({
    attackers: z.array(z.string()).describe("Pieces attacking the square, e.g., ['wQ', 'bN']"),
    defenders: z.array(z.string()).describe("Pieces defending the square, e.g., ['wR']"),
  }))).describe("An 8x8 matrix providing details for each square."),
});
export type GenerateInsightsInput = z.infer<typeof GenerateInsightsInputSchema>;

const GenerateInsightsOutputSchema = z.object({
  insights: z.string().describe('Insights about squares with complex tactical interdependencies.'),
});
export type GenerateInsightsOutput = z.infer<typeof GenerateInsightsOutputSchema>;

export async function generateInsights(input: GenerateInsightsInput): Promise<GenerateInsightsOutput> {
  return generateInsightsFlow(input);
}

const prompt = ai.definePrompt({
  name: 'generateInsightsPrompt',
  input: {schema: GenerateInsightsInputSchema},
  output: {schema: GenerateInsightsOutputSchema},
  prompt: `You are an expert chess analyst. You are given a chess position represented by a net influence matrix and a detailed breakdown of attackers and defenders for each square. Your task is to provide tactical insights.

  - The net influence matrix shows the balance of power on each square. Positive values favor White, negative values favor Black.
  - The detailed influence matrix shows exactly which pieces attack or defend each square. 'w' is White, 'b' is Black. (e.g., 'wQ' is White Queen, 'bN' is Black Knight).

  Analyze the provided data to identify key tactical situations:
  1.  **Contested Squares:** Find squares with high absolute net influence and many attackers/defenders. Explain the struggle for control.
  2.  **Pins and Skewers:** Look for situations where a high-value piece (like a King or Queen) is attacked, and another piece is on the same line of attack behind it.
  3.  **Forks:** Identify if a single piece is attacking two or more enemy pieces simultaneously.
  4.  **Undefended Pieces:** Highlight any attacking pieces that are themselves not defended. These are tactical liabilities.
  5.  **Overloaded Defenders:** Find pieces that are defending multiple other pieces or important squares.

  Provide a concise, actionable analysis based on these points. Focus on the most critical tactical features of the position.

  **Net Influence Matrix (White Positive, Black Negative):**
  {{json netInfluenceMatrix}}

  **Detailed Attackers/Defenders for each square:**
  {{json detailedInfluence}}
`,
});

const generateInsightsFlow = ai.defineFlow(
  {
    name: 'generateInsightsFlow',
    inputSchema: GenerateInsightsInputSchema,
    outputSchema: GenerateInsightsOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
