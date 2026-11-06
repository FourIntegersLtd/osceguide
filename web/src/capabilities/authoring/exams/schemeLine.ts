type SchemeVersion = { version: number; published_at?: string | null; structure: unknown };

/** "Good, Fair or Poor". */
function orList(items: string[]): string {
  if (items.length < 2) return items.join("");
  return `${items.slice(0, -1).join(", ")} or ${items[items.length - 1]}`;
}

/** The day, as the boards write it: "2 Oct". */
export function shortDay(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
}

const isObject = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);

/** The scale as words, from either form of the scheme; empty when it cannot be read. */
function scaleWords(structure: Record<string, unknown>): string {
  if (structure.schemaVersion === 3) {
    const scale = Array.isArray(structure.scales) ? structure.scales.find(isObject) : undefined;
    if (!scale) return "";
    if (Array.isArray(scale.levels)) {
      return orList(scale.levels.filter(isObject).map((l) => String(l.label ?? l.value)));
    }
    return typeof scale.from === "number" && typeof scale.to === "number" ? `${scale.from} to ${scale.to}` : "";
  }
  const rating = isObject(structure.rating) ? structure.rating : {};
  if (Array.isArray(rating.scale)) return orList(rating.scale.map(String));
  return rating.kind === "rag" ? orList(["G", "A", "R"]) : "";
}

/** "Version 3, published 2 Oct. 6 domains, rated Good, Fair or Poor." for a marking scheme version. */
export function schemeLine(v: SchemeVersion): string {
  const structure = isObject(v.structure) ? v.structure : {};
  const v3 = structure.schemaVersion === 3;
  const blocks = Array.isArray(v3 ? structure.outline : structure.sections) ? (v3 ? structure.outline : structure.sections) as unknown[] : [];
  const domains = blocks.filter((b) => isObject(b) && (v3 ? b.block : b.kind) === "domain").length;
  const scale = scaleWords(structure);
  const head = v.published_at ? `Version ${v.version}, published ${shortDay(v.published_at)}.` : `Version ${v.version}, not published.`;
  const parts = [head];
  if (domains > 0) {
    parts.push(`${domains} ${domains === 1 ? "domain" : "domains"}${scale ? `, rated ${scale}` : ""}.`);
  }
  return parts.join(" ");
}
