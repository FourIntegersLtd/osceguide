import { platformRequest } from "@/foundation/platform-client";
import type { components } from "@/foundation/platform-client";
import type { AttributionQuery, RevenueTimeBucket } from "@/capabilities/attribution-dashboard/types";
import { growthPartnerPath } from "@/capabilities/staff-growth/api";

/**
 * What a partner asks the backend.
 *
 * A partner is an organisation whose `org_type` is `partner`: they author
 * content for the platform's own catalogue rather than examining a cohort, and
 * they are measured by a funnel rather than by results. Everything here is the
 * reporter-gated `growth/*` half: a summary with a fee and no revenue, and series
 * over time. The routes refuse a reporter for any other partner. The funnel,
 * the tracking references and the reporter list are the same reads staff use,
 * so those come from `capabilities/staff-growth/api`.
 */

type S = components["schemas"];

export type PartnerSummary = S["PartnerDashboardSummaryRead"];
export type CountOverTime = S["CountOverTimeReport"];
export type FeeOverTime = S["FeeOverTimeReport"];


export function readPartnerSummary(
  partner: string,
  query: AttributionQuery,
  signal?: AbortSignal,
): Promise<PartnerSummary> {
  return platformRequest<PartnerSummary>(`${growthPartnerPath(partner)}/reporting/summary`, {
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
  return platformRequest<CountOverTime>(`${growthPartnerPath(partner)}/reporting/visits-over-time`, {
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
  return platformRequest<CountOverTime>(`${growthPartnerPath(partner)}/reporting/signups-over-time`, {
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
  return platformRequest<FeeOverTime>(`${growthPartnerPath(partner)}/reporting/fee-over-time`, {
    query: { ...query, bucket },
    signal,
  });
}
