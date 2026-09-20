type RecordValue = Record<string, unknown>;
const record = (value: unknown): RecordValue | null =>
  value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as RecordValue : null;
const strings = (value: unknown) =>
  value === undefined || (Array.isArray(value) && value.every((item) => typeof item === "string"));
const text = (value: unknown) => value === undefined || typeof value === "string";
const numericScore = (value: unknown, plab = false): boolean => {
  const row = record(value);
  return !!row && typeof row.score === "number" && Number.isFinite(row.score)
    && ["completed", "missed", "suggested_actions", "critical_flags", "evidence_points"].every((key) => strings(row[key]))
    && text(row.score_justification)
    && (text(row.supporting_phrase) || (plab && strings(row.supporting_phrase)))
    && (!plab || (row.score >= 0 && row.score <= 1));
};

export function feedbackExam(payload: RecordValue): "plab" | "casc" | "ortho" | null {
  const plabGroups = {
    data_gathering: ["history_taking", "examination", "investigations", "interpretation"],
    clinical_management: ["diagnosis", "management_plan", "safety_netting", "follow_up"],
    interpersonal_skills: ["language", "listening", "rapport", "empathy"],
  };
  if (Object.entries(plabGroups).every(([key, fields]) => {
    const group = record(payload[key]);
    return !!group && fields.every((field) => numericScore(group[field], true));
  })) return "plab";

  if (["history", "examination", "management", "communication"].every((key) => {
    const group = record(payload[key]);
    const narrative = record(group?.generic_domains);
    return !!group && !!narrative
      && Array.isArray(narrative.strengths) && narrative.strengths.every((item) => {
        const row = record(item);
        return !!row && typeof row.strength === "string" && typeof row.example === "string";
      })
      && Array.isArray(narrative.improvements) && narrative.improvements.every((item) => {
        const row = record(item);
        return !!row && typeof row.improvement === "string" && typeof row.issue === "string";
      })
      && Array.isArray(narrative.suggested_actions) && strings(narrative.suggested_actions)
      && Object.entries(group).filter(([name]) => name !== "generic_domains").every(([, item]) =>
        typeof record(item)?.competent === "boolean");
  })) return "casc";

  if (typeof payload.station_type === "string"
    && ["clinical", "prioritisation", "communication", "portfolio"].includes(payload.station_type)) {
    const skills = record(payload[`${payload.station_type}_skills`]);
    if (skills && Object.keys(skills).length && Object.values(skills).every((item) => numericScore(item))
      && (payload.station_total === undefined || typeof payload.station_total === "number")
      && text(payload.created_at)) return "ortho";
  }
  return null;
}
