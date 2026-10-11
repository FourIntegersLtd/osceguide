/**
 * Reading-time, excerpts and dates for study material.
 *
 * Brought across from the retiring client's `utils/blogExcerpt.ts` and
 * `utils/utcDate.ts`, which are the only two things the blog screens used them
 * for. They live beside the capability rather than in the foundation because
 * nothing else in this app needs them yet; the moment a second tier does, this
 * is the file that moves.
 */

/**
 * Bodies are markdown. Card previews used to slice the raw source, so excerpts
 * leaked `##`, `**`, link syntax and front-matter-ish noise. Strip the markup
 * to plain prose before truncating.
 */
export function excerpt(content: string, maxLength = 160): string {
  const plain = content
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/<[^>]+>/g, " ")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s{0,3}>\s?/gm, "")
    .replace(/^\s{0,3}([-*+]|\d+\.)\s+/gm, "")
    .replace(/[*_~]{1,3}/g, "")
    .replace(/\s+/g, " ")
    .trim();

  if (plain.length <= maxLength) return plain;
  const clipped = plain.slice(0, maxLength);
  const lastSpace = clipped.lastIndexOf(" ");
  return `${(lastSpace > 60 ? clipped.slice(0, lastSpace) : clipped).replace(/[,.;:\-–—]$/, "")}…`;
}

/** Rough read time for the card meta line. */
export function readMinutes(content: string): number {
  const words = content.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 220));
}

/**
 * Parse an API datetime as a UTC instant.
 *
 * A naive ISO string with no `Z` and no offset is UTC, matching the backend's
 * `datetime.utcnow().isoformat()`. Reading it as local time moved every
 * publication date by an hour each summer.
 */
function parseApiUtc(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const value = String(iso).trim();
  if (!value) return null;
  const hasZone = /[zZ]$/.test(value) || /[+-]\d{2}:?\d{2}$/.test(value);
  const date = new Date(hasZone || !value.includes("T") ? value : `${value}Z`);
  return Number.isFinite(date.getTime()) ? date : null;
}

/** Empty string when there is no date, so a meta line simply shortens. */
export function formatPublished(
  iso: string | null | undefined,
  options: Intl.DateTimeFormatOptions = { year: "numeric", month: "short", day: "numeric" },
): string {
  return parseApiUtc(iso)?.toLocaleDateString("en-GB", options) ?? "";
}

/** Most posts open with their own `# Title`; don't print it twice. */
export function leadsWithHeading(content: string): boolean {
  return /^\s*(#\s|<h1[\s>])/i.test(content);
}

/** Seconds as a player shows them: 171 reads "02:51". */
export function clockTime(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(whole / 60)).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
}

/**
 * A summary line written `Label: detail` split at the first ": ", so the label can be
 * bold. A line with no label has an empty `lead`.
 */
export function boldLead(entry: string): { lead: string; rest: string } {
  const colon = entry.indexOf(": ");
  if (colon === -1) return { lead: "", rest: entry };
  return { lead: entry.slice(0, colon + 1), rest: entry.slice(colon + 2) };
}
