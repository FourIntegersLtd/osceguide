import { platformRequest, type components } from "@/foundation/platform-client";
import type { AuthoringScope } from "@/capabilities/authoring/api/scope";
import { pathId } from "@/capabilities/authoring/api/scope";

type S = components["schemas"];

/* --------------------------------------------------------- station imports */

/**
 * One uploaded station document and how far its drafting has got.
 *
 * An import moves through `drafting_template`, `template_ready`,
 * `drafting_station` and `completed`, or stops at `failed` with an `error` a
 * person can read. Both drafting steps are background jobs, so every call here
 * answers a row and a status, never a finished template or station.
 */
export type StationImport = S["StationImportRead"];

/** This scope's most recent imports, newest first. */
export function listStationImports(
  scope: AuthoringScope,
  signal?: AbortSignal,
): Promise<S["StationImportList"]> {
  return platformRequest<S["StationImportList"]>(`${scope.base}/station-imports`, { signal });
}

/**
 * Upload one PDF or Word document.
 *
 * With no template version the first job drafts a template from the file and
 * stops for a person to review it. With a published template version the
 * import goes straight to drafting the station.
 */
export function uploadStationImport(
  scope: AuthoringScope,
  input: { file: File; examCode: string; templateVersionId?: string | null },
): Promise<StationImport> {
  const form = new FormData();
  // The field names are the backend's parameter names.
  form.append("file", input.file);
  form.append("exam_code", input.examCode);
  if (input.templateVersionId) form.append("template_version_id", input.templateVersionId);
  return platformRequest<StationImport>(`${scope.base}/station-imports`, {
    method: "POST",
    formData: form,
  });
}

/**
 * Draft the station for an import whose template has been published.
 *
 * Refused with `template_not_published` while the template is still a draft.
 */
export function draftStationFromImport(
  scope: AuthoringScope,
  importId: string,
): Promise<StationImport> {
  return platformRequest<StationImport>(
    `${scope.base}/station-imports/${pathId(importId)}/station`,
    { method: "POST" },
  );
}
