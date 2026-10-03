/** The sections whose name contains what was typed; everything when nothing was. */
export function matchingSections<T extends { label: string }>(items: T[], query: string): T[] {
  const needle = query.trim().toLowerCase();
  return needle ? items.filter((item) => item.label.toLowerCase().includes(needle)) : items;
}

/** The highlighted row after an arrow key: it stops at either end and never leaves an empty list. */
export function moveActive(index: number, key: "ArrowDown" | "ArrowUp", count: number): number {
  const next = key === "ArrowDown" ? index + 1 : index - 1;
  return Math.max(0, Math.min(next, count - 1));
}
