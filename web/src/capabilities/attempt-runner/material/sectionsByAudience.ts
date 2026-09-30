import type { components } from "@/foundation/platform-client";

export type AudienceSection = components["schemas"]["AudienceSectionRead"];
export type AudienceBlock = components["schemas"]["AudienceBlockRead"];
export type Audience = "candidate" | "patient" | "examiner";

/**
 * The part of these sections one audience reads. The examiner reads every
 * `examiner`-role block wherever the template filed it, so a candidate section
 * holding the model answer shows the brief open and the answer collapsed.
 */
export function sectionsFor(sections: AudienceSection[], audience: Audience): AudienceSection[] {
  return sections.flatMap((section) => {
    const blocks = section.blocks.filter((block) =>
      audience === "examiner"
        ? block.role === "examiner" || section.audience === "examiner"
        : block.role !== "examiner" && section.audience === audience,
    );
    return blocks.length > 0 ? [{ ...section, blocks }] : [];
  });
}

/** Every block as one `Label: text` line — context for a voice agent, not a screen. */
export function sectionLines(sections: AudienceSection[]): string[] {
  return sections.flatMap((section) =>
    section.blocks.flatMap((block) => {
      const text = asText(block.value);
      return text ? [`${block.label || block.id}: ${text}`] : [];
    }),
  );
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** `patient_list` → `Patient list`, for keys a template gave no label. */
export function humanise(key: string): string {
  const spaced = key.replace(/[_-]+/g, " ").trim();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** A value as one line of text, whatever shape it was authored in — mirrors `domain_audience._render_value`. */
export function asText(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value.trim();
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(asText).filter(Boolean).join("; ");
  if (isRecord(value)) {
    return Object.entries(value)
      .map(([key, sub]) => {
        const text = asText(sub);
        return text ? `${key}: ${text}` : "";
      })
      .filter(Boolean)
      .join(", ");
  }
  return String(value);
}
