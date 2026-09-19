import { platformRequest, type components } from "@/foundation/platform-client";
import type { AuthoringScope, Json } from "@/capabilities/authoring/api/scope";
import type { Station, StationVersion } from "@/capabilities/authoring/api/scope";
import { pathId } from "@/capabilities/authoring/api/scope";

type S = components["schemas"];

/* ---------------------------------------------------------------- stations */

export function listStations(
  scope: AuthoringScope,
  params: { cursor?: string | null; limit?: number } = {},
  signal?: AbortSignal,
): Promise<S["Page_StationRead_"]> {
  return platformRequest(`${scope.base}/stations`, {
    query: { cursor: params.cursor ?? undefined, limit: params.limit },
    signal,
  });
}

export function createStation(
  scope: AuthoringScope,
  body: { title: string; exam_code: string; content: Json; template_version_id?: string | null },
): Promise<Station> {
  return platformRequest(`${scope.base}/stations`, { method: "POST", body });
}

export function addStationVersion(scope: AuthoringScope, station: string): Promise<StationVersion> {
  return platformRequest(`${scope.base}/stations/${pathId(station)}/versions`, { method: "POST" });
}

export function editStationVersion(
  scope: AuthoringScope,
  station: string,
  version: number,
  content: Json,
): Promise<StationVersion> {
  return platformRequest(`${scope.base}/stations/${pathId(station)}/versions/${version}`, {
    method: "PATCH",
    body: { content },
  });
}

export function deleteStationVersion(
  scope: AuthoringScope,
  station: string,
  version: number,
): Promise<void> {
  return platformRequest(`${scope.base}/stations/${pathId(station)}/versions/${version}`, {
    method: "DELETE",
  });
}

export function archiveStationVersion(
  scope: AuthoringScope,
  station: string,
  version: number,
): Promise<StationVersion> {
  return platformRequest(`${scope.base}/stations/${pathId(station)}/versions/${version}/archive`, {
    method: "POST",
  });
}

export function publishStationVersion(
  scope: AuthoringScope,
  station: string,
  version: number,
): Promise<StationVersion> {
  return platformRequest(`${scope.base}/stations/${pathId(station)}/versions/${version}/publish`, {
    method: "POST",
  });
}

/**
 * Correct the reading brief without cutting a new version.
 *
 * The brief is what a candidate is handed before the station starts, so a typo
 * in one does not invalidate what everybody else was marked against.
 */
export function editStationBrief(
  scope: AuthoringScope,
  station: string,
  version: number,
  reading_brief: string,
): Promise<StationVersion> {
  return platformRequest(`${scope.base}/stations/${pathId(station)}/versions/${version}/brief`, {
    method: "PATCH",
    body: { reading_brief },
  });
}
