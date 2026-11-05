import { readRating } from "@/capabilities/authoring/rubrics/rubricEdits";

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

/** "Version 3, published 2 Oct. 6 areas, rated Good, Fair or Poor." for a marking scheme version. */
export function schemeLine(v: SchemeVersion): string {
  const structure = (typeof v.structure === "object" && v.structure !== null ? v.structure : {}) as Record<string, unknown>;
  const sections = Array.isArray(structure.sections) ? structure.sections : [];
  const areas = sections.filter((s) => typeof s === "object" && s !== null && (s as { kind?: unknown }).kind === "domain").length;
  const scale = readRating(structure as Parameters<typeof readRating>[0]).scale;
  const head = v.published_at ? `Version ${v.version}, published ${shortDay(v.published_at)}.` : `Version ${v.version}, not published.`;
  const parts = [head];
  if (areas > 0) parts.push(`${areas} ${areas === 1 ? "area" : "areas"}${scale.length > 0 ? `, rated ${orList(scale)}` : ""}.`);
  return parts.join(" ");
}
