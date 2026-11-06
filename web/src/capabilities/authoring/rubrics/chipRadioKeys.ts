/** Where focus goes when an arrow key is pressed on chip `at` of `count`; null for any other key. Arrows only move focus, they never choose. */
export function radioFocusTarget(count: number, at: number, key: string): number | null {
  if (count === 0) return null;
  const step = key === "ArrowRight" || key === "ArrowDown" ? 1 : key === "ArrowLeft" || key === "ArrowUp" ? -1 : 0;
  if (step === 0) return null;
  return (Math.max(at, 0) + step + count) % count;
}
