import { platformRequest, type components } from "@/foundation/platform-client";

export type Overview = components["schemas"]["PlatformOverview"];
export type Organization = components["schemas"]["OrganizationRead"];

export function readOverview(signal?: AbortSignal): Promise<Overview> {
  return platformRequest<Overview>("/api/v1/platform/overview", { signal });
}

export function listOrganizations(signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_OrganizationRead_"]>(
    "/api/v1/platform/organizations",
    { signal },
  );
}

export function listUsers(signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_UserSummary_"]>("/api/v1/platform/users", {
    signal,
  });
}

/**
 * Provision an organisation.
 *
 * `org_type` decides which console its members land in. There is no separate
 * employer product: a hiring organisation is one of these running exam-mode
 * sittings.
 */
export function createOrganization(input: {
  name: string;
  slug: string;
  orgType: string;
}): Promise<Organization> {
  return platformRequest<Organization>("/api/v1/platform/organizations", {
    method: "POST",
    body: { name: input.name, slug: input.slug, org_type: input.orgType },
  });
}

export function suspendOrganization(slug: string): Promise<void> {
  return platformRequest<void>(
    `/api/v1/platform/organizations/${encodeURIComponent(slug)}/suspend`,
    { method: "POST" },
  );
}

export function restoreOrganization(slug: string): Promise<void> {
  return platformRequest<void>(
    `/api/v1/platform/organizations/${encodeURIComponent(slug)}/restore`,
    { method: "POST" },
  );
}
