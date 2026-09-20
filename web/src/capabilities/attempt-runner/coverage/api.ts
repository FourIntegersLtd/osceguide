import { platformRequest, type components } from "@/foundation/platform-client";

export type CoverageUpdate = components["schemas"]["CoverageRead"];
export type CoverageItem = components["schemas"]["CoverageItemRead"];

export function readCoverage(attemptId: string, signal?: AbortSignal): Promise<CoverageUpdate> {
  return platformRequest(`/api/v1/attempts/${encodeURIComponent(attemptId)}/coverage`, { signal });
}
