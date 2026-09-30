import { platformRequest, type components } from "@/foundation/platform-client";
import type { AttributionQuery, RevenueTimeBucket } from "@/foundation/attribution/types";

type S = components["schemas"];

export type FunnelRead = S["FunnelRead"];
export type TrackingReference = S["TrackingReference"];
export type TrackingPage = S["Page_TrackingReference_"];
export type DashboardSummary = S["DashboardSummaryRead"];
export type RevenueOverTime = S["RevenueOverTimeReport"];
export type ArrivalRow = S["ArrivalRow"];
export type ArrivalPage = S["Page_ArrivalRow_"];
export type AcquiredUserRow = S["AcquiredUserRow"];
export type AcquiredUserPage = S["Page_AcquiredUserRow_"];
export type Reporter = S["ReporterRead"];
export type PilotConfig = S["PilotConfigRead"];
export type PilotConfigUpdate = S["UpdatePilotConfig"];

const growth = (partner: string) =>
  `/api/v1/growth/partners/${encodeURIComponent(partner)}`;

/** The summary every Overview, Revenue and How-we-count figure comes from. */
export function readDashboardSummary(
  partner: string,
  query: AttributionQuery,
  signal?: AbortSignal,
): Promise<DashboardSummary> {
  return platformRequest<DashboardSummary>(`${growth(partner)}/summary`, { query: { ...query }, signal });
}

export function readPartnerFunnel(
  partner: string,
  query: AttributionQuery,
  signal?: AbortSignal,
): Promise<FunnelRead> {
  return platformRequest<FunnelRead>(`${growth(partner)}/funnel`, { query: { ...query }, signal });
}

export function readRevenueOverTime(
  partner: string,
  query: AttributionQuery,
  bucket: RevenueTimeBucket,
  signal?: AbortSignal,
): Promise<RevenueOverTime> {
  return platformRequest<RevenueOverTime>(`${growth(partner)}/revenue-over-time`, {
    query: { ...query, bucket },
    signal,
  });
}

/** One page of landings. `search` is matched by the server, never over the rows already loaded. */
export function listArrivals(
  partner: string,
  query: AttributionQuery,
  options: { search: string; cursor: string | null },
  signal?: AbortSignal,
): Promise<ArrivalPage> {
  return platformRequest<ArrivalPage>(`${growth(partner)}/arrivals`, {
    query: { ...query, search: options.search || undefined, cursor: options.cursor },
    signal,
  });
}

/** One page of sign-ups, for the same dates, exam and campaign as every other number. */
export function listAcquiredUsers(
  partner: string,
  query: AttributionQuery,
  cursor: string | null,
  signal?: AbortSignal,
): Promise<AcquiredUserPage> {
  return platformRequest<AcquiredUserPage>(`${growth(partner)}/acquired-users`, {
    query: { ...query, cursor },
    signal,
  });
}

export function listPartnerRefIds(
  partner: string,
  signal?: AbortSignal,
): Promise<TrackingPage> {
  return platformRequest<TrackingPage>(`${growth(partner)}/ref-ids`, { signal });
}

export function listPartnerReporters(partner: string, signal?: AbortSignal): Promise<Reporter[]> {
  return platformRequest<Reporter[]>(`${growth(partner)}/reporters`, { signal });
}

export function addPartnerReporter(partner: string, email: string): Promise<void> {
  return platformRequest<void>(`${growth(partner)}/reporters`, {
    method: "POST",
    body: { email },
  });
}

export function revokePartnerReporter(partner: string, email: string): Promise<void> {
  return platformRequest<void>(`${growth(partner)}/reporters/${encodeURIComponent(email)}`, {
    method: "DELETE",
  });
}

export function readPilotConfig(partner: string, signal?: AbortSignal): Promise<PilotConfig> {
  return platformRequest<PilotConfig>(`${growth(partner)}/pilot-config`, { signal });
}

export function updatePilotConfig(
  partner: string,
  update: PilotConfigUpdate,
): Promise<PilotConfig> {
  return platformRequest<PilotConfig>(`${growth(partner)}/pilot-config`, {
    method: "PATCH",
    body: update,
  });
}
