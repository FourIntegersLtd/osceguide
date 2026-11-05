/** The ways to start a station, as the New station chooser offers them. */

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
    body: "Describe the case in a few lines.",
    next: "Write the brief. The AI drafts the station; check it, run a fact check, then publish.",
    cta: "Write a brief",
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
    next: "Opens the form with your exam chosen. Add a layout there if you want one, or write the sections yourself.",
    cta: "Open the builder",
  },
];

/** The create form, opened on the way the author chose, with the exam already picked. */
export function stationStartHref(newPath: string, way: StationStartWay, examCode: string): string {
  const query = [`start=${way}`, examCode ? `exam=${encodeURIComponent(examCode)}` : ""].filter(Boolean);
  return `${newPath}?${query.join("&")}`;
}

/** The form shows once a way is chosen, or a published template is already named (back from the template wizard). */
export function showsCreateForm(params: { get(name: string): string | null }): boolean {
  return params.get("start") !== null || params.get("templateVersion") !== null;
}
