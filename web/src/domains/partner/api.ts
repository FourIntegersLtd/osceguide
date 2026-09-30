import { platformRequest } from "@/foundation/platform-client";
import type { components } from "@/foundation/platform-client";
import type { AttributionQuery, RevenueTimeBucket } from "@/foundation/attribution/types";

/**
 * What a partner asks the backend.
 *
 * A partner is an organisation whose `org_type` is `partner`: they author
 * content for the platform's own catalogue rather than examining a cohort, and
 * they are measured by a funnel rather than by results. Everything here is the
 * reporter-gated `growth/*` half: a summary with a fee and no revenue, series
 * over time, and the funnel. The routes refuse a reporter for any other partner.
 */

type S = components["schemas"];

export type PartnerFunnel = S["FunnelRead"];
export type RefIdPage = S["Page_TrackingReference_"];
export type PartnerSummary = S["PartnerDashboardSummaryRead"];
export type CountOverTime = S["CountOverTimeReport"];
export type FeeOverTime = S["FeeOverTimeReport"];

const growth = (partner: string) =>
  `/api/v1/growth/partners/${encodeURIComponent(partner)}`;

export function readFunnel(
  partner: string,
  query: AttributionQuery,
  signal?: AbortSignal,
): Promise<PartnerFunnel> {
  return platformRequest<PartnerFunnel>(`${growth(partner)}/funnel`, { query: { ...query }, signal });
}

export function readPartnerSummary(
  partner: string,
  query: AttributionQuery,
  signal?: AbortSignal,
): Promise<PartnerSummary> {
  return platformRequest<PartnerSummary>(`${growth(partner)}/reporting/summary`, {
    query: { ...query },
    signal,
  });
}

export function readVisitsOverTime(
  partner: string,
  query: AttributionQuery,
  bucket: RevenueTimeBucket,
  signal?: AbortSignal,
): Promise<CountOverTime> {
  return platformRequest<CountOverTime>(`${growth(partner)}/reporting/visits-over-time`, {
    query: { ...query, bucket },
    signal,
  });
}

export function readSignupsOverTime(
  partner: string,
  query: AttributionQuery,
  bucket: RevenueTimeBucket,
  signal?: AbortSignal,
): Promise<CountOverTime> {
  return platformRequest<CountOverTime>(`${growth(partner)}/reporting/signups-over-time`, {
    query: { ...query, bucket },
    signal,
  });
}

export function readFeeOverTime(
  partner: string,
  query: AttributionQuery,
  bucket: RevenueTimeBucket,
  signal?: AbortSignal,
): Promise<FeeOverTime> {
  return platformRequest<FeeOverTime>(`${growth(partner)}/reporting/fee-over-time`, {
    query: { ...query, bucket },
    signal,
  });
}

export function listRefIds(partner: string, signal?: AbortSignal): Promise<RefIdPage> {
  return platformRequest<RefIdPage>(`${growth(partner)}/ref-ids`, { signal });
}

export function addReporter(partner: string, email: string): Promise<void> {
  return platformRequest<void>(`${growth(partner)}/reporters`, {
    method: "POST",
    body: { email },
  });
}
