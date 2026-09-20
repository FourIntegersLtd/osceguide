/** Patient name and biodata for the consultation card — matches legacy `patientIdentity`. */

const NAME_TITLES = new Set([
  "mr",
  "mrs",
  "ms",
  "miss",
  "mx",
  "dr",
  "prof",
  "master",
]);

const GENDER_WORDS = new Set(["male", "female", "man", "woman"]);

export interface ConsultationPatient {
  name: string;
  detail: string | null;
  initials: string;
}

export function parsePatientIdentity(
  biodata: string | undefined,
  gender: string | undefined,
): { name: string | null; detail: string; initials: string } {
  const parts = (biodata ?? "")
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);

  const genderLabel = gender
    ? gender.charAt(0).toUpperCase() + gender.slice(1).toLowerCase()
    : null;

  if (parts.length === 0) {
    return { name: null, initials: "?", detail: genderLabel ?? "" };
  }

  const name = parts[0]!;
  const rest = parts.slice(1);
  const words = name
    .split(/\s+/)
    .filter((word) => !NAME_TITLES.has(word.replace(/\./g, "").toLowerCase()));
  const initials =
    words
      .slice(0, 2)
      .map((word) => word.charAt(0).toUpperCase())
      .join("") || name.charAt(0).toUpperCase();

  const descriptors = rest.filter((part) => !GENDER_WORDS.has(part.toLowerCase()));
  if (genderLabel) descriptors.splice(1, 0, genderLabel);

  return { name, initials, detail: descriptors.join(" · ") };
}

/**
 * Who the candidate sees in the consultation column — same rules as legacy
 * `stationPatientIdentity` (biodata line under the name, not the station title).
 */
export function consultationPatientFromBrief(brief: {
  patient?: { name_line?: string | null; gender?: string | null };
  doctor_information?: { patient_biodata?: string | null } | null;
} | null | undefined): ConsultationPatient {
  if (!brief) {
    return { name: "Your patient", detail: null, initials: "?" };
  }

  const biodata =
    brief.doctor_information?.patient_biodata?.trim() ||
    brief.patient?.name_line?.trim() ||
    undefined;

  const parsed = parsePatientIdentity(biodata, brief.patient?.gender ?? undefined);
  const name = parsed.name ?? "Your patient";
  const detail = parsed.detail.trim() ? parsed.detail : null;

  return { name, detail, initials: parsed.initials };
}
