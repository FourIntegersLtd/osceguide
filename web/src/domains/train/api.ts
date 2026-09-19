import { platformRequest, type components } from "@/foundation/platform-client";

export type Dashboard = components["schemas"]["Dashboard"];
export type StationSet = components["schemas"]["SetRead"];
export type SetPage = components["schemas"]["Page_SetRead_"];
export type SetEntry = components["schemas"]["EntryRead"];
export type StartedAttempt = components["schemas"]["StartedAttempt"];
export type Entitlement = components["schemas"]["EntitlementSummary"];
export type Plan = components["schemas"]["PlanRead"];

/** The whole home screen in one request. */
export function readDashboard(signal?: AbortSignal): Promise<Dashboard> {
  return platformRequest<Dashboard>("/api/v1/me/dashboard", { signal });
}

export function listSets(signal?: AbortSignal): Promise<SetPage> {
  return platformRequest<SetPage>("/api/v1/me/station-sets", { signal });
}

export function readSet(setId: string, signal?: AbortSignal): Promise<StationSet> {
  return platformRequest<StationSet>(`/api/v1/me/station-sets/${encodeURIComponent(setId)}`, {
    signal,
  });
}

export function createSet(input: {
  name: string;
  examCode: string;
  stationVersionIds: string[];
}): Promise<StationSet> {
  return platformRequest<StationSet>("/api/v1/me/station-sets", {
    method: "POST",
    body: {
      name: input.name,
      exam_code: input.examCode,
      station_version_ids: input.stationVersionIds,
    },
  });
}

/**
 * Start an attempt at one entry.
 *
 * The counter is incremented in SQL inside the attempt's transaction, so two
 * taps cannot both be allowed past the limit.
 */
export function startSetAttempt(setId: string, entryId: string): Promise<StartedAttempt> {
  return platformRequest<StartedAttempt>(
    `/api/v1/me/station-sets/${encodeURIComponent(setId)}/entries/${encodeURIComponent(entryId)}/attempts`,
    { method: "POST" },
  );
}

export function listEntitlements(signal?: AbortSignal) {
  return platformRequest<{ items: Entitlement[] }>("/api/v1/me/entitlements", { signal });
}

export function listPlans(signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_PlanRead_"]>("/api/v1/billing/plans", {
    signal,
  });
}
