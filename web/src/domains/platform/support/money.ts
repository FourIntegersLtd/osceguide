/** "12", "12.5" or "£12.50" as pence; null for a blank or unreadable entry, never NaN. */
export function penceFrom(text: string): number | null {
  const cleaned = text.trim().replace(/^£\s*/, "").replace(/,/g, "");
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) return null;
  return Math.round(Number(cleaned) * 100);
}

/** Pence as pounds with two decimals, such as "£12.50". */
export function poundsLabel(pence: number): string {
  return `£${(pence / 100).toFixed(2)}`;
}

/** What the confirm step says was paid: "free" for a blank or zero amount, otherwise "£12.50". */
export function amountPaidLabel(pence: number | null): string {
  return pence === null || pence === 0 ? "free" : poundsLabel(pence);
}
