/** The ways to start a station, as the New station chooser offers them. */

import { matchesExamFilter } from "@/capabilities/authoring/parts/examCatalogFilter";

export type StationStartWay = "layout" | "import" | "ai" | "library" | "blank";

export const STATION_START_WAYS: readonly {
  id: StationStartWay;
  title: string;
  body: string;
  next: string;
  cta: string;
}[] = [
  {
    id: "layout",
    title: "From a layout",
    body: "Yours, or one of OSCE Guide’s. Sections are set out for you.",
    next: "Pick a layout, then write the station in the builder: patient, examiner, marking, photos, preview and versions.",
    cta: "Choose a layout",
  },
  {
    id: "import",
    title: "Import a PDF or Word file",
    body: "We read your document and draft the station from it.",
    next: "Upload the file. When it has been read, review the draft in the builder before publishing.",
    cta: "Upload a file",
  },
  {
    id: "ai",
    title: "Draft with AI from a brief",
    body: "Pick a layout, then describe the case in a few lines.",
    next: "Pick a published layout first, then write the brief, check the draft and publish.",
    cta: "Choose a layout",
  },
  {
    id: "library",
    title: "Copy from the library",
    body: "Copy one of OSCE Guide’s stations into your organisation.",
    next: "Browse the library, then \"Copy to my organisation\". The copy is yours to change.",
    cta: "Browse the library",
  },
  {
    id: "blank",
    title: "Start blank",
    body: "Write every section yourself.",
    next: "Opens the form with your exam chosen. Add a layout there or write the sections.",
    cta: "Open the builder",
  },
];

/** The create form, opened on the way the author chose, with the exam already picked. */
export function stationStartHref(newPath: string, way: StationStartWay, examCode: string): string {
  const query = [`start=${way}`, examCode ? `exam=${encodeURIComponent(examCode)}` : ""].filter(Boolean);
  return `${newPath}?${query.join("&")}`;
}

/**
 * The form shows once a way is chosen, or a published template is already named (back from the
 * template wizard). The chooser is the organisation's: the staff console keeps the form directly.
 */
export function showsCreateForm(
  params: { get(name: string): string | null },
  scopeKind: "org" | "platform",
): boolean {
  return scopeKind !== "org" || params.get("start") !== null || params.get("templateVersion") !== null;
}

/**
 * The templates the form may offer. With an exam carried from the chooser, only that exam's (and
 * unscoped ones), so choosing a template cannot swap the exam. A named template (deep link) is never narrowed.
 */
export function templatesForChosenExam<T extends { exam_code?: string | null }>(
  templates: readonly T[],
  params: { get(name: string): string | null },
): T[] {
  const exam = params.get("exam");
  if (!exam || params.get("templateVersion")) return [...templates];
  return templates.filter((t) => matchesExamFilter(t.exam_code, exam, { includeUnscoped: true }));
}
