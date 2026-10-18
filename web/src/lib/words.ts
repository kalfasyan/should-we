// How the app talks about numbers.

/** Priority levels, stored as weights 0–5. */
export const LEVELS = [
  { value: 0, label: "Don't care" },
  { value: 1, label: 'A little' },
  { value: 3, label: 'Important' },
  { value: 5, label: 'Must-have' },
] as const;

/** The level shown for a stored weight (2 and 4 came from v1 data). */
export function levelOf(weight: number | undefined): number {
  const w = weight ?? 3;
  let best: number = LEVELS[0].value;
  for (const l of LEVELS) {
    const d = Math.abs(l.value - w);
    const bestD = Math.abs(best - w);
    if (d < bestD || (d === bestD && l.value > best)) best = l.value;
  }
  return best;
}

/** One-word description of a 0–5 rating. */
export function ratingWord(v: number): string {
  if (v < 1) return 'Bad';
  if (v < 2) return 'Poor';
  if (v < 3) return 'OK';
  if (v < 4) return 'Good';
  if (v < 5) return 'Great';
  return 'Perfect';
}

export function formatScore(score: number): string {
  return score.toFixed(1);
}

/** Notes that are links become clickable. */
export function asLink(note: string): string | null {
  return /^https?:\/\/\S+$/.test(note.trim()) ? note.trim() : null;
}

export const EXAMPLES: { name: string; title: string; features: string[] }[] = [
  { name: '🏠 Home', title: 'Which apartment should we rent?', features: ['Price', 'Location', 'Size', 'Condition', 'Commute'] },
  { name: '🚗 Car', title: 'Which car should we buy?', features: ['Price', 'Fuel economy', 'Safety', 'Space', 'Looks'] },
  { name: '🏖️ Holiday', title: 'Where should we go on holiday?', features: ['Price', 'Weather', 'Activities', 'Food', 'Travel time'] },
  { name: '💻 Laptop', title: 'Which laptop should I get?', features: ['Price', 'Performance', 'Battery life', 'Weight', 'Screen'] },
];
