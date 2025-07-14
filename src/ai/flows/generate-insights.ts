// src/ai/flows/generate-insights.ts
'use server';

/**
 * @fileOverview Flow to generate insights about squares with complex tactical interdependencies.
 *
 * - generateInsights - A function that takes the net influence matrix and returns insights about squares with complex tactical interdependencies.
 * - GenerateInsightsInput - The input type for the generateInsights function.
 * - GenerateInsightsOutput - The return type for the generateInsights function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const GenerateInsightsInputSchema = z.object({
  netInfluenceMatrix: z
    .array(z.array(z.number()))
    .describe('The net influence matrix of the chessboard.'),
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
  prompt: `You are an expert chess analyst. Analyze the provided net influence matrix and identify squares where the net influence is strongly affected by multiple pieces.

Net Influence Matrix:
{{#each netInfluenceMatrix}}
  {{this}}
{{/each}}

Provide a concise description of these squares and the tactical interdependencies involved. Focus on the squares with the highest absolute values and explain why they are significant.
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
