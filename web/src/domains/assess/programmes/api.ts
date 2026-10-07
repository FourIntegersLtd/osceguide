import { platformRequest, type components } from "@/foundation/platform-client";
import { orgPath } from "@/domains/assess/api";

export type PlatformCatalogueExam = components["schemas"]["PlatformCatalogueExamRead"];
export type PlatformCatalogue = components["schemas"]["PlatformCatalogueRead"];
export type ImportedExam = components["schemas"]["ImportedExamRead"];

/** The platform's published exams, each marked with whether this organisation already runs it. */
export function listPlatformCatalogue(slug: string, signal?: AbortSignal): Promise<PlatformCatalogue> {
  return platformRequest<PlatformCatalogue>(`${orgPath(slug)}/exams/catalog`, { signal });
}

/**
 * Adopt a platform exam by reference: the server records an active programme
 * naming it, and nothing is copied. Refused `unknown_exam` (404) for anything
 * not currently published by the platform, `exam_already_imported` (409) when
 * this organisation already runs it.
 */
export function importPlatformExam(slug: string, platformExamId: string): Promise<ImportedExam> {
  return platformRequest<ImportedExam>(`${orgPath(slug)}/exams/import`, {
    method: "POST",
    body: { platform_exam_id: platformExamId },
  });
}
