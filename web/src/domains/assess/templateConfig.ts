import type { components } from "@/foundation/platform-client";
import type { ScheduleDraft } from "@/domains/assess/scheduleSitting";
import type { Programme } from "@/domains/assess/api";
import { clampBreakMinutes, clampBreaks, clampReadingMinutes } from "@/domains/assess/timing";

export type TemplateConfig = components["schemas"]["TemplateConfig"];

/** What a template keeps of a schedule: the setup, never a date, a person or a named assessor. */
export function toTemplateConfig(draft: ScheduleDraft): TemplateConfig {
  return {
    programme_id: draft.programmeId || null,
    mode: draft.mode,
    stations: draft.stations.map((s) => ({ version_id: s.version_id, title: s.title })),
    reading_minutes: draft.readingMinutes,
    consultation_minutes: draft.consultationMinutes,
    break_minutes: draft.breakMinutes,
    breaks: draft.mode === "exam" ? draft.breaks.map((b) => ({ after: b.after, minutes: b.minutes })) : [],
    assessor_style: draft.mode === "exam" && draft.perCandidate ? "per_candidate" : "one",
  };
}

/**
 * The draft fields a template fills in. The exam is kept only if it is still ready to schedule;
 * otherwise the draft keeps its own exam and no stations (they belonged to the old one).
 */
export function fromTemplateConfig(
  config: TemplateConfig,
  ready: readonly Pick<Programme, "id">[],
  current: Pick<ScheduleDraft, "programmeId">,
): Partial<ScheduleDraft> {
  const stillReady = config.programme_id != null && ready.some((p) => p.id === config.programme_id);
  const mode = config.mode === "exam" ? "exam" : "training";
  const stations = stillReady ? (config.stations ?? []) : [];
  return {
    programmeId: stillReady ? (config.programme_id as string) : current.programmeId,
    mode,
    stations: stations.map((s) => ({ version_id: s.version_id, title: s.title })),
    readingMinutes: clampReadingMinutes(config.reading_minutes),
    consultationMinutes: config.consultation_minutes,
    breakMinutes: clampBreakMinutes(config.break_minutes),
    breaks:
      mode === "exam"
        ? clampBreaks(
            (config.breaks ?? []).map((b) => b.after),
            stations.length,
          ).map((after) => ({
            after,
            minutes: clampBreakMinutes(config.breaks?.find((b) => b.after === after)?.minutes ?? config.break_minutes),
          }))
        : [],
    perCandidate: mode === "exam" && config.assessor_style === "per_candidate",
    supervisorByCandidate: {},
  };
}
