import { platformRequest } from "@/foundation/platform-client";
import { VISITOR_KEY_COOKIE_NAME } from "@/foundation/attribution/partnerConstants";
import type { components } from "@/foundation/platform-client";

type AcquisitionRead = components["schemas"]["AcquisitionRead"];

/**
 * Spending the visitor key on the account it just became.
 *
 * `POST /api/v1/growth/acquisitions` exists because registration cannot reach
 * the `growth` slice from inside itself — it sits below it — so crediting a
 * signup is a second call the client makes once it holds a token. Nothing did
 * that in the first cut of this port, which is the other half of why partner
 * reporting went dark: an arrival with no signup attached is a visitor nobody
 * sold.
 *
 * It must never be visible to the person registering. A referral is why they
 * arrived, not a step they agreed to, and a failed POST here says nothing they
 * can act on — the account exists either way. So every outcome is swallowed
 * except the one the backend says is normal: `null`, no acquisition to credit,
 * which is most signups.
 */
export function readVisitorKey(): string | null {
  if (typeof document === "undefined") return null;
  const entry = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${VISITOR_KEY_COOKIE_NAME}=`));
  if (!entry) return null;
  const value = decodeURIComponent(entry.slice(VISITOR_KEY_COOKIE_NAME.length + 1));
  return value.length > 0 && value.length <= 64 ? value : null;
}

/** Credits the new account to the partner who sent them. Resolves either way. */
export async function creditThisSignup(): Promise<AcquisitionRead | null> {
  const visitorKey = readVisitorKey();
  if (!visitorKey) return null;
  try {
    return await platformRequest<AcquisitionRead | null>("/api/v1/growth/acquisitions", {
      method: "POST",
      body: { visitor_key: visitorKey },
    });
  } catch {
    return null;
  }
}
