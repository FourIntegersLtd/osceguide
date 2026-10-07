export type HandClaim = { claim: string; source: string };

/**
 * One claim per line, written `claim || source`. A line with no source is refused by name rather
 * than sent: a claim checked by hand without the page it was checked against has not been checked.
 */
export function parseHandClaims(
  text: string,
): { claims: HandClaim[]; error: null } | { claims: null; error: string } {
  const claims: HandClaim[] = [];
  const lines = text.split("\n");
  for (const [index, raw] of lines.entries()) {
    const line = raw.trim();
    if (!line) continue;
    const [claim, source] = line.split("||").map((part) => part.trim());
    if (!claim || !source) {
      return { claims: null, error: `Line ${index + 1} needs a claim and its source: claim || source.` };
    }
    claims.push({ claim, source });
  }
  if (claims.length === 0) return { claims: null, error: "Add at least one claim." };
  return { claims, error: null };
}
