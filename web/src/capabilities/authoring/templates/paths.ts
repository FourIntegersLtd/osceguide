/** Authoring template flows live outside the tabbed `/authoring/{section}` shell. */

export function stationTemplatesListPath(hrefFor: (path: string) => string): string {
  return `${hrefFor("/authoring")}/station-templates`;
}

/** The new-template wizard, with the exam already chosen when the caller knows it. */
export function stationTemplateNewPath(
  hrefFor: (path: string) => string,
  examCode?: string | null,
  options: { thenStation?: boolean } = {},
): string {
  const base = `${stationTemplatesListPath(hrefFor)}/new`;
  const query = [
    examCode ? `exam=${encodeURIComponent(examCode)}` : "",
    options.thenStation ? "then=station" : "",
  ].filter(Boolean);
  return query.length ? `${base}?${query.join("&")}` : base;
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

export function rubricEditPath(hrefFor: (path: string) => string, rubricId: string, version: number): string {
  return `${rubricsListPath(hrefFor)}/${encodeURIComponent(rubricId)}/versions/${version}`;
}
