import { platformRequest } from "@/foundation/platform-client";

export type StationGenerationProfileSummary = {
  profileKey: string;
  label: string;
  examCode: string | null;
  orthoStationType: string | null;
};

export type StationGenerationProfileDetail = StationGenerationProfileSummary & {
  systemPrompt: string;
  blockHints: Record<string, string>;
};

export async function listStationGenerationProfiles(): Promise<StationGenerationProfileSummary[]> {
  const res = await platformRequest<{ items: StationGenerationProfileSummary[] }>(
    "/api/v1/station-generation-profiles",
  );
  return res.items ?? [];
}

export async function getStationGenerationProfile(
  profileKey: string,
): Promise<StationGenerationProfileDetail> {
  return platformRequest<StationGenerationProfileDetail>(
    `/api/v1/station-generation-profiles/${encodeURIComponent(profileKey)}`,
  );
}
