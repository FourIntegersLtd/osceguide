/** "12", "12.5" or "£12.50" as pence; null for a blank or unreadable entry, never NaN. */
export function penceFrom(text: string): number | null {
  const cleaned = text.trim().replace(/^£\s*/, "").replace(/,/g, "");
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) return null;
  return Math.round(Number(cleaned) * 100);
}
