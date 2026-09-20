import { platformRequest, type components } from "@/foundation/platform-client";
import type { AuthoringScope, Json } from "@/capabilities/authoring/api/scope";
import type { Station, StationVersion } from "@/capabilities/authoring/api/scope";
import { pathId } from "@/capabilities/authoring/api/scope";

type S = components["schemas"];

/* ---------------------------------------------------------------- stations */

const STATION_PAGE_LIMIT = 100;
const STATION_MAX_PAGES = 25;

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

/** Walk cursors until the library is in memory — same pattern as org roster lists. */
export async function listAllStations(scope: AuthoringScope, signal?: AbortSignal): Promise<Station[]> {
  const items: Station[] = [];
  let cursor: string | null = null;
  for (let index = 0; index < STATION_MAX_PAGES; index += 1) {
    const page = await listStations(scope, { limit: STATION_PAGE_LIMIT, cursor }, signal);
    items.push(...(page.items as Station[]));
    cursor = page.next_cursor ?? null;
    if (!cursor) break;
  }
  return items;
}

export function autogenerateStationDraft(
  scope: AuthoringScope,
  body: { prompt: string; template_version_id: string },
): Promise<{ suggested_title: string; content: Record<string, unknown> }> {
  return platformRequest(`${scope.base}/stations/autogenerate-draft`, {
    method: "POST",
    body,
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
