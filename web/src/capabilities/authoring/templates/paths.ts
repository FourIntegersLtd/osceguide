/** Authoring template flows live outside the tabbed `/authoring/{section}` shell. */

export function stationTemplatesListPath(hrefFor: (path: string) => string): string {
  return `${hrefFor("/authoring")}/station-templates`;
}

/** Query marker: the wizard was opened from station creation and returns there when saved. */
const THEN_STATION = "station";

export function isThenStation(value: string | null): boolean {
  return value === THEN_STATION;
}

function wizardPath(hrefFor: (path: string) => string, examCode?: string | null, then?: string): string {
  const query = [examCode ? `exam=${encodeURIComponent(examCode)}` : "", then ? `then=${then}` : ""]
    .filter(Boolean)
    .join("&");
  return `${stationTemplatesListPath(hrefFor)}/new${query ? `?${query}` : ""}`;
}

/** The new-template wizard, with the exam already chosen when the caller knows it. */
export function stationTemplateNewPath(hrefFor: (path: string) => string, examCode?: string | null): string {
  return wizardPath(hrefFor, examCode);
}

/** The same wizard, finishing by publishing and going back to station creation. */
export function stationTemplateThenStationPath(hrefFor: (path: string) => string, examCode: string): string {
  return wizardPath(hrefFor, examCode, THEN_STATION);
}

export function stationTemplateEditPath(
  hrefFor: (path: string) => string,
  templateId: string,
  version: number,
): string {
  return `${stationTemplatesListPath(hrefFor)}/${encodeURIComponent(templateId)}/versions/${version}`;
}

export function feedbackTemplatesListPath(hrefFor: (path: string) => string): string {
  return `${hrefFor("/authoring")}/feedback-templates`;
}

export function feedbackTemplateNewPath(hrefFor: (path: string) => string): string {
  return `${feedbackTemplatesListPath(hrefFor)}/new`;
}

export function feedbackTemplateEditPath(
  hrefFor: (path: string) => string,
  templateId: string,
  version: number,
): string {
  return `${feedbackTemplatesListPath(hrefFor)}/${encodeURIComponent(templateId)}/versions/${version}`;
}

/** The rubric builder: a start screen, then one version at a time. */
export function rubricsListPath(hrefFor: (path: string) => string): string {
  return `${hrefFor("/authoring")}/rubrics`;
}

export function rubricNewPath(hrefFor: (path: string) => string): string {
  return `${rubricsListPath(hrefFor)}/new`;
}

export function rubricEditPath(
  hrefFor: (path: string) => string,
  rubricId: string,
  version: number,
  examId?: string | null,
): string {
  return `${rubricsListPath(hrefFor)}/${encodeURIComponent(rubricId)}/versions/${version}${examQuery(examId)}`;
}

/** `?exam=<id>`: the exam sheet that sent the author here, carried until the scheme is published. */
function examQuery(examId?: string | null): string {
  return examId ? `?exam=${encodeURIComponent(examId)}` : "";
}

/** Back to the New exam sheet, resuming the exam it left (Phase 2a owns that page). */
export function examResumePath(hrefFor: (path: string) => string, examId: string): string {
  return `${hrefFor("/authoring")}/exams/new${examQuery(examId)}`;
}
