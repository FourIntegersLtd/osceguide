/** The layout a station was written from: its template's title, found through the template version it names. */
export function layoutName(
  templates: readonly { title: string; versions: readonly { id: string }[] }[],
  templateVersionId: string | null | undefined,
): string | null {
  if (!templateVersionId) return null;
  return templates.find((template) => template.versions.some((version) => version.id === templateVersionId))?.title ?? null;
}
