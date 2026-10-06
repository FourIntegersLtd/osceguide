/**
 * How money and dates are written across the product.
 *
 * Every screen formats through here so a price or a date reads the same
 * wherever it is shown.
 */

/** Shown in place of a date that is missing or cannot be read. */
const NO_DATE = "-";

/** "£24.99" from pence. Pounds unless the payment names another currency. */
export function formatMoney(pence: number, currency = "GBP"): string {
  const amount = pence / 100;
  try {
    return new Intl.NumberFormat("en-GB", {
      style: "currency",
      currency: currency.toUpperCase(),
    }).format(amount);
  } catch {
    // An unknown currency code makes Intl throw; show the number rather than break the page.
    return `${amount.toFixed(2)} ${currency.toUpperCase()}`;
  }
}

/**
 * Read a timestamp from the API.
 *
 * The API sends some timestamps with no time zone, and those are UTC. A
 * browser would read them as local time and show every one an hour out in
 * summer, so a time with no zone is read as UTC here.
 */
export function parseApiDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const text = String(iso).trim();
  const hasZone = /[zZ]$/.test(text) || /[+-]\d{2}:?\d{2}$/.test(text);
  const parsed = new Date(hasZone || !text.includes("T") ? text : `${text}Z`);
  return Number.isFinite(parsed.getTime()) ? parsed : null;
}

/** "26 September 2026". */
export function formatLongDate(iso: string | null | undefined): string {
  const date = parseApiDate(iso);
  if (!date) return NO_DATE;
  return date.toLocaleDateString("en-GB", { year: "numeric", month: "long", day: "numeric" });
}

/** "26 September 2026 at 18:44". */
export function formatLongDateTime(iso: string | null | undefined): string {
  const date = parseApiDate(iso);
  if (!date) return NO_DATE;
  return date.toLocaleDateString("en-GB", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** "20 Nov 2026, 09:00", in the reader's own time zone. */
export function formatShortDateTime(iso: string | null | undefined): string {
  const date = parseApiDate(iso);
  if (!date) return NO_DATE;
  return date.toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
