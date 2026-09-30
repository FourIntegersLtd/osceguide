import { platformRequest } from "@/foundation/platform-client";
import type { components } from "@/foundation/platform-client";

/**
 * What a partner asks the backend.
 *
 * A partner is an organisation whose `org_type` is `partner`: they author
 * content for the platform's own catalogue rather than examining a cohort, and
 * they are measured by a funnel rather than by results. Both halves are
 * already served — `growth/*` for the funnel, the org catalogue endpoints for
 * the authoring — so this arm is a shell and a dashboard over work the backend
 * had before the frontend had an arm for it.
 */

export type PartnerFunnel = components["schemas"]["FunnelRead"];
export type RefIdPage = components["schemas"]["Page_TrackingReference_"];

export function readFunnel(partner: string, signal?: AbortSignal): Promise<PartnerFunnel> {
  return platformRequest<PartnerFunnel>(
    `/api/v1/growth/partners/${encodeURIComponent(partner)}/funnel`,
    { signal },
  );
}

export function listRefIds(partner: string, signal?: AbortSignal): Promise<RefIdPage> {
  return platformRequest<RefIdPage>(
    `/api/v1/growth/partners/${encodeURIComponent(partner)}/ref-ids`,
    { signal },
  );
}

export function addReporter(partner: string, email: string): Promise<void> {
  return platformRequest<void>(
    `/api/v1/growth/partners/${encodeURIComponent(partner)}/reporters`,
    { method: "POST", body: { email } },
  );
}
