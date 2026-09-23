import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes"; /** Client-side mirror of backend validate_station_content (required blocks + types). */
export function validateStationContent(
  structure: StationStructure,
  content: Record<string, unknown>,
): { ok: true } | { ok: false; errors: string[] } {
  const errors: string[] = [];
  for (const section of structure.sections || []) {
    for (const block of section.blocks || []) {
      const bid = block.id;
      const btype = block.type;
      const required = !!(block as { required?: boolean }).required;
      if (!bid) continue;
      const value = content[bid];
      if (
        required &&
        (value === undefined ||
          value === null ||
          value === "" ||
          (Array.isArray(value) && value.length === 0))
      ) {
        const label = (block as { label?: string }).label || bid;
        errors.push(`"${label}" Is required`);
        continue;
      }
      if (value === undefined || value === null) continue;
      if (btype === "shortText" || btype === "longText") {
        if (typeof value !== "string") errors.push(`"${bid}" Must be text`);
      } else if (btype === "list") {
        if (!Array.isArray(value)) errors.push(`"${bid}" Must be a list`);
      } else if (btype === "singleSelect") {
        const opts = ((block as { options?: string[] }).options || []).map(
          String,
        );
        if (
          typeof value !== "string" ||
          (opts.length > 0 && !opts.includes(value))
        ) {
          errors.push(`"${bid}" Must be a valid option`);
        }
      } else if (btype === "multiSelect" || btype === "checklist") {
        if (!Array.isArray(value)) errors.push(`"${bid}" Must be a list`);
      } else if (btype === "scale") {
        if (typeof value !== "number") errors.push(`"${bid}" Must be a number`);
      }
    }
  }
  return errors.length === 0 ? { ok: true } : { ok: false, errors };
}
