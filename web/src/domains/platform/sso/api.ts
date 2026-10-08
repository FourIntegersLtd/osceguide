import { hasCode, platformRequest, type components } from "@/foundation/platform-client";

export type SamlConnection = components["schemas"]["SamlConnectionRead"];
/** The server keeps (or defaults) any claim attribute left out; the generated type predates that. */
type ClaimAttribute = "email_attribute" | "first_name_attribute" | "last_name_attribute" | "display_name_attribute";
export type SaveSamlInput = Omit<
  components["schemas"]["SaveSamlConnection"],
  ClaimAttribute
> &
  Partial<
    Pick<
      components["schemas"]["SaveSamlConnection"],
      ClaimAttribute
    >
  >;

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
