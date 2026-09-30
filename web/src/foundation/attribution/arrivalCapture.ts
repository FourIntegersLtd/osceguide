import type { NextRequest, NextResponse } from "next/server";
import {
  VISITOR_KEY_COOKIE_NAME,
  VISITOR_KEY_COOKIE_MAX_AGE_DAYS,
} from "@/foundation/attribution/partnerConstants";
import type { ParsedReferralParams } from "@/foundation/attribution/partnerTypes";

/**
 * First-touch partner attribution, at the edge.
 *
 * A partner's link is the whole commercial relationship: `utm_source=<partner>`
 * plus a `ref_id`, and the numbers the partner is billed on are the arrivals and
 * the signups that carry them. The retiring client did this at its edge, and
 * this port shipped with the parser and the cookie names but nothing that used them — so a visitor arriving from BMJ was recorded
 * nowhere, and `POST /api/v1/growth/arrivals` had no caller in the product.
 *
 * It runs here rather than in a landing component because a referral landing is
 * exactly the request where the browser may have no JavaScript at all, and
 * because the value has to exist before the person reaches the register form.
 *
 * What did **not** come across is the signed acquisition cookie. That existed so
 * the old backend could hand the edge a token it alone had issued; platform-api
 * asks for no signature — `RecordArrival` takes an opaque `visitor_key` and
 * `CreditSignup` takes the same one — so a key generated here and never read
 * from anywhere but a cookie is the whole of what the contract needs. If the
 * platform ever wants it unforgeable, that is a backend endpoint, not a client.
 */

/** One arrival, as `POST /growth/arrivals` wants it. */
export interface ArrivalPayload {
  partner: string;
  visitor_key: string;
  ref_id: string | null;
  landing_path: string;
  utm: Record<string, string>;
}

export function toArrivalPayload(parsed: ParsedReferralParams, visitorKey: string): ArrivalPayload {
  const utm: Record<string, string> = { source: parsed.partner };
  if (parsed.utmMedium) utm.medium = parsed.utmMedium;
  if (parsed.utmCampaign) utm.campaign = parsed.utmCampaign;
  return {
    partner: parsed.partner,
    visitor_key: visitorKey,
    ref_id: parsed.refId,
    landing_path: parsed.landingPath,
    utm,
  };
}

/**
 * The visitor's key, minting one when this is their first arrival.
 *
 * First-touch by construction: an existing cookie is never overwritten, so the
 * partner who sent them once keeps the credit however they come back.
 */
export function resolveVisitorKey(request: NextRequest): {
  visitorKey: string;
  isFirstTouch: boolean;
} {
  const existing = request.cookies.get(VISITOR_KEY_COOKIE_NAME)?.value;
  if (existing && existing.length <= 64) return { visitorKey: existing, isFirstTouch: false };
  return { visitorKey: crypto.randomUUID(), isFirstTouch: true };
}

export function applyVisitorKeyCookie(
  response: NextResponse,
  visitorKey: string,
  secure: boolean,
): void {
  response.cookies.set(VISITOR_KEY_COOKIE_NAME, visitorKey, {
    maxAge: VISITOR_KEY_COOKIE_MAX_AGE_DAYS * 24 * 60 * 60,
    path: "/",
    sameSite: "lax",
    secure,
    // Readable by the browser on purpose: the register step is what spends it,
    // and `POST /growth/acquisitions` is an authenticated call the edge cannot
    // make on a person's behalf.
    httpOnly: false,
  });
}

/**
 * Record this arrival.
 *
 * Returns nothing that matters. An arrival is an accounting entry, not a page:
 * a slow or failed POST must never delay or fail the response the visitor is
 * waiting on, so the caller hands the promise to `waitUntil` and answers the
 * browser first.
 */
export async function recordArrival(
  parsed: ParsedReferralParams,
  visitorKey: string,
  origin: string,
): Promise<void> {
  try {
    await fetch(`${origin}/api/v1/growth/arrivals`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(toArrivalPayload(parsed, visitorKey)),
    });
  } catch (error) {
    // The cookie is already set, so the signup still credits when they register.
    console.error("[attribution] arrival not recorded", error);
  }
}
