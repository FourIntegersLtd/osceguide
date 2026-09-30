import type {
  StationStructure,
  StationTemplateStartPoint,
} from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

/** Maps template start points to platform generation profile keys. */
export const START_POINT_PROFILE_KEY: Record<StationTemplateStartPoint, string> = {
  blank: "custom",
  asterix: "sca.station",
  sca: "sca.station",
  plab: "plab.station",
  casc: "casc.station",
  ortho: "ortho.clinical",
  ortho_prioritisation: "ortho.prioritisation",
  ortho_communication: "ortho.communication",
  ortho_portfolio: "ortho.portfolio",
};

export const EXAM_DEFAULT_PROFILE_KEY: Record<string, string> = {
  sca: "sca.station",
  plab: "plab.station",
  casc: "casc.station",
  ortho: "ortho.clinical",
};

export function profileKeyForStartPoint(start: StationTemplateStartPoint): string {
  return START_POINT_PROFILE_KEY[start] ?? "sca.station";
}

export function profileKeyForExamCode(examCode: string | null | undefined): string {
  const code = (examCode ?? "sca").trim().toLowerCase();
  return EXAM_DEFAULT_PROFILE_KEY[code] ?? "sca.station";
}

/** Inverse of {@link START_POINT_PROFILE_KEY} for swapping layout when exam type changes. */
export function startPointForProfileKey(profileKey: string): StationTemplateStartPoint | null {
  const key = profileKey.trim();
  if (!key || key === "custom") return null;
  for (const [start, mapped] of Object.entries(START_POINT_PROFILE_KEY) as [
    StationTemplateStartPoint,
    string,
  ][]) {
    if (start === "blank" || start === "asterix") continue;
    if (mapped === key) return start;
  }
  return null;
}

export function withStationGeneration(
  structure: StationStructure,
  profileKey: string,
): StationStructure {
  return {
    ...structure,
    generation: { profileKey },
  };
}
