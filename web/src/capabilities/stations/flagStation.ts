import { platformRequest } from "@/foundation/platform-client";

/** Ask the content team to review a library station. */
export async function flagStation(stationId: string, signal?: AbortSignal): Promise<void> {
  await platformRequest(`/api/v1/me/station-flags`, {
    method: "POST",
    body: JSON.stringify({ station_id: stationId }),
    signal,
  });
}
