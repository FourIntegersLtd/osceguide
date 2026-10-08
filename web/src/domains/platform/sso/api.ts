import { hasCode, platformRequest, type components } from "@/foundation/platform-client";

export type SamlConnection = components["schemas"]["SamlConnectionRead"];
export type SaveSamlInput = components["schemas"]["SaveSamlConnection"];

const path = (slug: string) => `/api/v1/platform/orgs/${encodeURIComponent(slug)}/sso/saml`;

/** The organisation's SAML identity provider, or null while none is set up (or SSO itself is not). */
export async function readSamlConnection(slug: string, signal?: AbortSignal): Promise<SamlConnection | null> {
  try {
    return await platformRequest<SamlConnection>(path(slug), { signal });
  } catch (cause) {
    if (hasCode(cause, "saml_connection_not_found", "sso_not_configured")) return null;
    throw cause;
  }
}

export function saveSamlConnection(slug: string, input: SaveSamlInput): Promise<SamlConnection> {
  return platformRequest<SamlConnection>(path(slug), { method: "PUT", body: input });
}
