/**
 * Which writes a rubric version offers. The server refuses publishing anything
 * but a draft, archiving anything but a published version, and any write by an
 * organisation to a platform rubric; offering them only made a button that
 * always failed.
 */
export function rubricVersionActions(
  status: string,
  { platformOwned, orgScope }: { platformOwned: boolean; orgScope: boolean },
): { publish: boolean; archive: boolean } {
  if (platformOwned && orgScope) return { publish: false, archive: false };
  return { publish: status === "draft", archive: status === "published" };
}
