/** Authoring template flows live outside the tabbed `/authoring/{section}` shell. */

export function stationTemplatesListPath(hrefFor: (path: string) => string): string {
  return `${hrefFor("/authoring")}/station-templates`;
}

export function stationTemplateNewPath(hrefFor: (path: string) => string): string {
  return `${stationTemplatesListPath(hrefFor)}/new`;
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
