import type { StationTemplateStartPoint } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { defaultStartPointForExam } from "@/capabilities/authoring/structure/b2b/lib/stations/stationTemplatePresets";

export type StationTemplateStartOption = {
  id: StationTemplateStartPoint;
  title: string;
  description: string;
  featuredForOrgSlugs?: readonly string[];
  /** Exam codes this layout belongs to. Omitted = always shown (blank). */
  examCodes?: readonly string[];
};

export type OrderedStationTemplateStartOption = StationTemplateStartOption & {
  recommended: boolean;
};

/** Starting layouts for station content templates (patient packs, station fields). */
export const STATION_TEMPLATE_START_OPTIONS: readonly StationTemplateStartOption[] =
  [
    {
      id: "blank",
      title: "Blank",
      description: "Start from scratch",
    },
    {
      id: "sca",
      title: "SCA",
      description: "Patient, record, plan",
      examCodes: ["sca"],
    },
    {
      id: "plab",
      title: "PLAB 2",
      description: "Brief, patient, plan",
      examCodes: ["plab"],
    },
    {
      id: "casc",
      title: "CASC",
      description: "Brief, patient, plan",
      examCodes: ["casc"],
    },
    {
      id: "ortho",
      title: "Clinical interview",
      description: "Scenario, work-up, Q&A",
      examCodes: ["ortho"],
    },
    {
      id: "ortho_prioritisation",
      title: "Prioritisation",
      description: "Trauma list and ordering",
      examCodes: ["ortho"],
    },
    {
      id: "ortho_communication",
      title: "Communication",
      description: "Consent, news, conduct",
      examCodes: ["ortho"],
    },
    {
      id: "ortho_portfolio",
      title: "Portfolio",
      description: "Brief and CV interview",
      examCodes: ["ortho"],
    },
  ];

/** Starting layouts for feedback / examiner marking templates. */
export const FEEDBACK_TEMPLATE_START_OPTIONS: readonly StationTemplateStartOption[] =
  [
    {
      id: "blank",
      title: "Blank",
      description: "Empty marking form",
    },
    {
      id: "sca",
      title: "SCA",
      description: "R/A/G criteria",
      examCodes: ["sca"],
    },
    {
      id: "plab",
      title: "PLAB 2",
      description: "GMC domain scores",
      examCodes: ["plab"],
    },
    {
      id: "casc",
      title: "CASC",
      description: "Competent / not competent",
      examCodes: ["casc"],
    },
    {
      id: "ortho",
      title: "Ortho",
      description: "0–10 competency scores",
      examCodes: ["ortho"],
    },
  ];

export function defaultStartPointForOrg(
  orgSlug: string,
  options: readonly StationTemplateStartOption[],
): StationTemplateStartPoint {
  const featured = options.find((option) =>
    option.featuredForOrgSlugs?.includes(orgSlug),
  );
  return featured?.id ?? "blank";
}

/** Layouts for this exam, plus unscoped ones (blank). Unknown/empty exam → unscoped only. */
export function startOptionsForExam(
  examCode: string | null | undefined,
  options: readonly StationTemplateStartOption[],
): StationTemplateStartOption[] {
  const code = examCode?.trim().toLowerCase() ?? "";
  return options.filter((option) => {
    if (!option.examCodes?.length) return true;
    return code !== "" && option.examCodes.includes(code);
  });
}

/** Prefer ?exam= when present; otherwise org-featured or blank. */
export function initialStationStartPoint(
  orgSlug: string,
  examCode: string | null | undefined,
): StationTemplateStartPoint {
  return (
    defaultStartPointForExam(examCode) ??
    defaultStartPointForOrg(orgSlug, STATION_TEMPLATE_START_OPTIONS)
  );
}

/** Prefer ?exam= when present for feedback templates. */
export function initialFeedbackStartPoint(
  orgSlug: string,
  examCode: string | null | undefined,
): StationTemplateStartPoint {
  const fromExam = defaultStartPointForExam(examCode);
  if (fromExam && fromExam !== "blank" && fromExam !== "asterix") {
    return fromExam;
  }
  return defaultStartPointForOrg(orgSlug, FEEDBACK_TEMPLATE_START_OPTIONS);
}

export function orderedStartOptions(
  orgSlug: string,
  options: readonly StationTemplateStartOption[],
): OrderedStationTemplateStartOption[] {
  const featured = options.filter((option) =>
    option.featuredForOrgSlugs?.includes(orgSlug),
  );
  const featuredIds = new Set(featured.map((option) => option.id));
  const rest = options.filter((option) => !featuredIds.has(option.id));

  return [
    ...featured.map((option) => ({ ...option, recommended: true })),
    ...rest.map((option) => ({ ...option, recommended: false })),
  ];
}
