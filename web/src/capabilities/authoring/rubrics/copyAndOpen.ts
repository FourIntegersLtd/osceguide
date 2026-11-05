import { copyRubric, type AuthoringScope } from "@/capabilities/authoring/api";
import { rubricEditPath } from "@/capabilities/authoring/templates/paths";

type CopyBody = Parameters<typeof copyRubric>[1];

/** Copy (or start blank), then open the new draft's first version in the builder. */
export async function copyAndOpen(
  scope: AuthoringScope,
  push: (href: string) => void,
  hrefFor: (path: string) => string,
  body: CopyBody,
  examId: string | null,
): Promise<void> {
  const copy = await copyRubric(scope, body);
  push(rubricEditPath(hrefFor, copy.id, (copy.versions ?? [])[0]?.version ?? 1, examId));
}
