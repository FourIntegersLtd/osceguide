import type { B2CSegmentedTabItem } from "@/foundation/ui";

export const AUTHORING_SECTIONS = [
  { id: "stations", label: "Stations" },
  { id: "station-templates", label: "Station templates" },
  { id: "rubrics", label: "Rubrics" },
  { id: "exams", label: "Exams" },
  { id: "programmes", label: "Programmes" },
] as const;

export type AuthoringSection = (typeof AUTHORING_SECTIONS)[number]["id"];

export function parseAuthoringSection(value: string | undefined): AuthoringSection | null {
  if (!value) return null;
  return AUTHORING_SECTIONS.some((item) => item.id === value)
    ? (value as AuthoringSection)
    : null;
}

export function authoringTabItems(
  includeProgrammes: boolean,
): B2CSegmentedTabItem<AuthoringSection>[] {
  return AUTHORING_SECTIONS.filter(
    (item) => item.id !== "programmes" || includeProgrammes,
  ).map(({ id, label }) => ({ id, label }));
}
