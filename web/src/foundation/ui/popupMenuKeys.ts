/** The item to focus for a key pressed in a menu: `disabled` flags every item, `at` is the focused one (-1 for none). Disabled items are skipped; null for other keys. */
export function menuFocusTarget(disabled: readonly boolean[], at: number, key: string): number | null {
  const enabled = disabled.flatMap((off, n) => (off ? [] : [n]));
  if (enabled.length === 0) return null;
  const position = enabled.indexOf(at);
  if (key === "Home") return enabled[0] ?? null;
  if (key === "End") return enabled[enabled.length - 1] ?? null;
  if (key === "ArrowDown") return enabled[(position + 1) % enabled.length] ?? null;
  if (key === "ArrowUp") return enabled[position <= 0 ? enabled.length - 1 : position - 1] ?? null;
  return null;
}
