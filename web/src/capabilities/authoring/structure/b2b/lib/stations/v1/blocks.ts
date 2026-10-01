import type { StationBlock } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

const SCA_RAG_OPTIONS = ["R", "A", "G"] as const;
const COMPETENT_OPTIONS = ["Competent", "Not competent"] as const;

export function ragBlock(pathStem: string, label: string): StationBlock {
  return {
    id: pathStem.replace(/\./g, "_"),
    type: "ragCriterion",
    label,
    pathStem,
  };
}

export function scaleBlock(
  id: string,
  label: string,
  min: number,
  max: number,
): StationBlock {
  return {
    id,
    type: "scale",
    label,
    min,
    max,
  };
}

export function competentBlock(pathStem: string, label: string): StationBlock {
  return {
    id: pathStem.replace(/\./g, "_"),
    type: "singleSelect",
    label,
    options: [...COMPETENT_OPTIONS],
  };
}

export function domainSummaryBlocks(pathStem: string, label: string): StationBlock[] {
  const base = pathStem.replace(/\./g, "_");
  return [
    {
      id: `${base}_score`,
      type: "singleSelect",
      label: `${label}: Overall score`,
      options: [...SCA_RAG_OPTIONS],
    },
    {
      id: `${base}_strengths`,
      type: "list",
      label: `${label}: Strengths`,
    },
    {
      id: `${base}_improvements`,
      type: "list",
      label: `${label}: Improvements`,
    },
    {
      id: `${base}_suggested_actions`,
      type: "list",
      label: `${label}: Suggested actions`,
    },
  ];
}

/** PLAB 2 numeric competency (0–1) with evidence lists. */
export function plabCompetencyBlocks(
  domainId: string,
  competencyId: string,
  label: string,
): StationBlock[] {
  const prefix = `${domainId}_${competencyId}`;
  return [
    scaleBlock(`${prefix}_score`, `${label}: Score`, 0, 1),
    {
      id: `${prefix}_completed`,
      type: "list",
      label: `${label}: Completed`,
    },
    {
      id: `${prefix}_supporting_phrase`,
      type: "list",
      label: `${label}: Supporting phrases`,
    },
    {
      id: `${prefix}_missed`,
      type: "list",
      label: `${label}: Missed`,
    },
    {
      id: `${prefix}_suggested_actions`,
      type: "list",
      label: `${label}: Suggested actions`,
    },
    {
      id: `${prefix}_critical_flags`,
      type: "list",
      label: `${label}: Critical flags`,
    },
  ];
}

/** Ortho interview competency (0–10) aligned to seeded rubric ids. */
export function orthoCompetencyBlocks(
  _domainId: string,
  rubricCompetencyId: string,
  label: string,
): StationBlock[] {
  const prefix = rubricCompetencyId.replace(/\./g, "_");
  return [
    scaleBlock(`${prefix}_score`, `${label}: Score`, 0, 10),
    {
      id: `${prefix}_score_justification`,
      type: "longText",
      label: `${label}: Score justification`,
    },
    {
      id: `${prefix}_evidence_points`,
      type: "list",
      label: `${label}: Evidence points`,
    },
    {
      id: `${prefix}_completed`,
      type: "list",
      label: `${label}: Completed`,
    },
    {
      id: `${prefix}_suggested_actions`,
      type: "list",
      label: `${label}: Suggested actions`,
    },
  ];
}

export function cascGenericDomainBlocks(domainId: string): StationBlock[] {
  return [
    {
      id: `${domainId}_generic_domains_strengths`,
      type: "list",
      label: "Strengths (narrative)",
    },
    {
      id: `${domainId}_generic_domains_improvements`,
      type: "list",
      label: "Improvements (narrative)",
    },
    {
      id: `${domainId}_generic_domains_suggested_actions`,
      type: "list",
      label: "Suggested actions",
    },
  ];
}
