const PARTNER_DISPLAY_NAMES: Record<string, string> = {
  bmj: "BMJ On Exam",
};

/** Human-readable partner name for a slug ("bmj" → "BMJ On Exam"). */
export function partnerDisplayName(slug: string | null | undefined): string {
  if (!slug) return "our partner";
  const key = slug.toLowerCase();
  return PARTNER_DISPLAY_NAMES[key] ?? key.replace(/[-_]+/g, " ").toUpperCase();
}
