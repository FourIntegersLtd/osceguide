/** Station authoring flows outside the tabbed `/authoring/{section}` shell. */

export function stationsListPath(hrefFor: (path: string) => string): string {
  return `${hrefFor("/authoring")}/stations`;
}

/** The station library, where an author browses stations to copy. */
export function stationLibraryPath(hrefFor: (path: string) => string): string {
  return hrefFor("/stations");
}

/** The create screen, with a published template version already chosen when the caller has one. */
export function stationNewPath(hrefFor: (path: string) => string, templateVersionId?: string | null): string {
  const base = `${stationsListPath(hrefFor)}/new`;
  return templateVersionId ? `${base}?templateVersion=${encodeURIComponent(templateVersionId)}` : base;
}

/** The Stations tab narrowed to one exam, by its code. */
export function stationsForExamPath(hrefFor: (path: string) => string, examCode: string): string {
  return `${stationsListPath(hrefFor)}?exam=${encodeURIComponent(examCode)}`;
}

/** The New station chooser with the exam already picked. */
export function stationNewForExamPath(hrefFor: (path: string) => string, examCode: string): string {
  return `${stationsListPath(hrefFor)}/new?exam=${encodeURIComponent(examCode)}`;
}
