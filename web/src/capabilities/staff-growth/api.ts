import { platformRequest, type components } from "@/foundation/platform-client";

type S = components["schemas"];

export type FunnelRead = S["FunnelRead"];
export type TrackingReference = S["TrackingReference"];
export type TrackingPage = S["Page_TrackingReference_"];

const growth = (partner: string) =>
  `/api/v1/growth/partners/${encodeURIComponent(partner)}`;

export function readPartnerFunnel(partner: string, signal?: AbortSignal): Promise<FunnelRead> {
  return platformRequest<FunnelRead>(`${growth(partner)}/funnel`, { signal });
}

export function listPartnerRefIds(
  partner: string,
  signal?: AbortSignal,
): Promise<TrackingPage> {
  return platformRequest<TrackingPage>(`${growth(partner)}/ref-ids`, { signal });
}

export function addPartnerReporter(partner: string, email: string): Promise<void> {
  return platformRequest<void>(`${growth(partner)}/reporters`, {
    method: "POST",
    body: { email },
  });
}
