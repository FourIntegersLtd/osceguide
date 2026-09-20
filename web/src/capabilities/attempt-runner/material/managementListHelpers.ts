/** ASCII/full stop + common Unicode dash marks (minus, en/em dash, etc.) */
const DOT = ".\\uFF0E";
const DASH = "\\u002D\\u2010-\\u2015\\u2212\\uFE58\\uFE63\\uFF0D";
const RE_BULLET = new RegExp(`^[•·▪▫◦‣⁃∙]\\s*`, "u");
const RE_DOT_DASH = new RegExp(`^[${DOT}]\\s*[${DASH}]\\s*`);
const RE_DOT_DASH_TIGHT = new RegExp(`^[${DOT}][${DASH}]\\s*`);
const RE_MARKDOWN_DASH = new RegExp(`^[${DASH}]\\s+`);
/** Don't strip leading "-" On lines like "1) …" / "2. …" */
const RE_NUMBERED_PREFIX = /^\d+\s*[).]\s/;
const RE_NUMBERED_HEADING = /^\d+[\).]\s*\S/;
export type PreparedListItem = {
  text: string;
  isNumberedHeading: boolean;
}; /** * Strip redundant list/markdown markers when <ul className="list-disc"> already renders bullets. * Peels chained prefixes (e.g. "• . - …") in a single pass loop until stable. */
export function normalizeListLine(line: string): string {
  let s = line;
  for (;;) {
    const before = s;
    s = s.trimStart();
    s = s.replace(RE_BULLET, "");
    s = s.replace(RE_DOT_DASH, "");
    s = s.replace(RE_DOT_DASH_TIGHT, "");
    if (!RE_NUMBERED_PREFIX.test(s)) {
      s = s.replace(RE_MARKDOWN_DASH, "");
    }
    if (s === before) return s.trimEnd();
  }
} /** One pass over newlines; computes heading flag from first line without re-splitting. */
export function prepareListItem(raw: string): PreparedListItem {
  const lines = raw.split(/\r?\n/);
  const normalized = lines.map(normalizeListLine);
  const text = normalized.join("\n").trim();
  const firstLine = normalized[0]?.trim() ?? "";
  return { text, isNumberedHeading: RE_NUMBERED_HEADING.test(firstLine) };
}
