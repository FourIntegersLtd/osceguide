import {
  platformRequest,
  rememberPlatformSession,
  type components,
} from "@/foundation/platform-client";

/**
 * Everything the account capability asks the backend.
 *
 * One module because the person is one subject: who they are, what they may
 * practise, what they paid, who they referred and what the tutor remembers.
 * The retiring client spread these across `databaseHelpers`, two axios
 * instances and seven components calling them inline.
 */

export type Me = components["schemas"]["UserRead"];
export type Entitlement = components["schemas"]["EntitlementSummary"];
export type Plan = components["schemas"]["PlanRead"];
export type Receipt = components["schemas"]["ReceiptRead"];
export type Referral = components["schemas"]["ReferralRead"];
export type TutorMemory = components["schemas"]["TutorMemoryRead"];
export type TutorNote = components["schemas"]["NoteRead"];
export type TutorEvent = components["schemas"]["EventRead"];
export type ForgottenCounts = components["schemas"]["ForgottenCounts"];

export function readMe(signal?: AbortSignal): Promise<Me> {
  return platformRequest<Me>("/api/v1/me", { signal });
}

export function listEntitlements(signal?: AbortSignal): Promise<{ items: Entitlement[] }> {
  return platformRequest<{ items: Entitlement[] }>("/api/v1/me/entitlements", { signal });
}

export function listPlans(signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_PlanRead_"]>("/api/v1/billing/plans", {
    signal,
  });
}

/**
 * Send somebody to pay, and say where.
 *
 * The client names a **plan code** and nothing else — no price, no amount, no
 * currency. The retiring checkout posted the pence it had rendered and the
 * backend matched them against a hardcoded table, so a price change broke the
 * purchase *after* the card was charged. The plan row owns the price here.
 *
 * Nothing is granted by this call. Access arrives when Stripe's webhook says
 * the money did, which is why the return page confirms rather than assumes.
 */
export function startCheckout(planCode: string): Promise<{ checkout_url: string }> {
  return platformRequest<components["schemas"]["CheckoutStarted"]>("/api/v1/billing/checkout", {
    method: "POST",
    body: { plan_code: planCode },
    // A double-submitted button is one intent to buy, not two.
    idempotencyKey: `checkout:${planCode}`,
  });
}

/**
 * The receipts this person has.
 *
 * `/me/receipts` answers a page of receipt **ids**, not documents — the
 * detail is a second call per id, scoped to the caller because a receipt id
 * travels to accountants and employers and must not be a key that anybody
 * holding it can read.
 */
export async function listReceipts(signal?: AbortSignal): Promise<Receipt[]> {
  const page = await platformRequest<components["schemas"]["Page_str_"]>(
    "/api/v1/me/receipts",
    { signal },
  );
  return Promise.all(page.items.map((id) => readReceipt(id, signal)));
}

export function readReceipt(receiptId: string, signal?: AbortSignal): Promise<Receipt> {
  return platformRequest<Receipt>(`/api/v1/me/receipts/${encodeURIComponent(receiptId)}`, {
    signal,
  });
}

/**
 * The receipt as a document, as markup rather than an object.
 *
 * The route answers `text/html` deliberately — a browser can print that to
 * PDF, where a `Content-Disposition: attachment` would stop somebody simply
 * looking at it. `Accept` has to say so or the client asks for JSON and the
 * server's content negotiation has nothing to honour.
 */
export function readReceiptDocument(receiptId: string, signal?: AbortSignal): Promise<string> {
  return platformRequest<string>(
    `/api/v1/me/receipts/${encodeURIComponent(receiptId)}/document`,
    { headers: { Accept: "text/html" }, signal },
  );
}

export function readReferrals(signal?: AbortSignal): Promise<Referral> {
  return platformRequest<Referral>("/api/v1/me/referrals", { signal });
}

/** One code per person; asking again returns the one they have. */
export function issueReferralCode(): Promise<Referral> {
  return platformRequest<Referral>("/api/v1/me/referral-code", { method: "POST" });
}

export function redeemReferral(code: string): Promise<void> {
  return platformRequest<void>("/api/v1/me/referrals/redeem", {
    method: "POST",
    body: { code },
  });
}

export function readTutorMemory(signal?: AbortSignal): Promise<TutorMemory> {
  return platformRequest<TutorMemory>("/api/v1/me/tutor-memory", { signal });
}

/**
 * Forget the lot, and say how much was forgotten.
 *
 * Debrief summaries are opt-in on the way out: they are also this doctor's own
 * record of what a debrief concluded, shown on their results, so clearing the
 * tutor's memory does not silently delete them unless asked.
 */
export function forgetTutorMemory(includeDebriefs: boolean): Promise<ForgottenCounts> {
  return platformRequest<ForgottenCounts>("/api/v1/me/tutor-memory", {
    method: "DELETE",
    query: { include_debriefs: includeDebriefs },
  });
}

export function forgetTutorNote(noteId: string): Promise<void> {
  return platformRequest<void>(
    `/api/v1/me/tutor-memory/notes/${encodeURIComponent(noteId)}`,
    { method: "DELETE" },
  );
}

export type UpdateMe = components["schemas"]["UpdateMe"];

/**
 * Change what is a person's own to change.
 *
 * Only the fields named are written — the backend reads `model_fields_set`, so
 * a panel that edits one thing does not silently clear the others. That is why
 * this takes a partial rather than the whole profile.
 */
export function updateMe(body: UpdateMe, signal?: AbortSignal): Promise<Me> {
  return platformRequest<Me>("/api/v1/me", { method: "PATCH", body, signal });
}

export type SsoSignIn = components["schemas"]["SsoSignIn"];
export type SsoSession = components["schemas"]["SsoSession"];

/**
 * Whether this visitor's organisation signs in somewhere else.
 *
 * `GET /auth/sso/sign-in?host=…` (or `?email=…`) is unauthenticated, because
 * it is what a sign-in page asks before anybody has signed in. It replaced the
 * retiring client's hostname allow-list compiled into the bundle.
 *
 * A `404` (`sso_not_configured`) is the ordinary answer — "sign in here, with
 * a password" — so it resolves to `null` rather than raising, and any other
 * failure does the same: this is a *display* rule for whether to draw the
 * password form, and a discovery failure must never lock somebody out of the
 * password sign-in that is the default. Callers branch on `null`, not on a
 * message.
 */
export async function readSsoSignIn(
  query: { host?: string; email?: string },
  signal?: AbortSignal,
): Promise<SsoSignIn | null> {
  try {
    return await platformRequest<SsoSignIn>("/api/v1/auth/sso/sign-in", {
      query: { host: query.host, email: query.email },
      signal,
    });
  } catch {
    return null;
  }
}

/**
 * Where to send the browser to sign in to that organisation.
 *
 * `POST /auth/sso/login` is unauthenticated like the read above it — it is the
 * first step of signing in, before anybody has — and it returns a URL rather
 * than following it, because the frontend owns navigation and the platform sets
 * no cookies. The broker is told to come back to `/auth/sso/callback`, which is
 * this app's own page.
 *
 * Unlike discovery, a failure here *is* the caller's problem: the button was
 * pressed expecting a redirect, so the error propagates rather than being
 * swallowed into a null.
 */
export async function startSsoSignIn(orgSlug: string): Promise<string> {
  const result = await platformRequest<components["schemas"]["SsoLoginResult"]>(
    "/api/v1/auth/sso/login",
    { method: "POST", body: { org_slug: orgSlug } },
  );
  return result.sign_in_url;
}

/**
 * Finish the sign-in the broker started.
 *
 * The token arrives on the query string of the callback page. It is posted to
 * the backend and **verified there** — the platform decodes nothing itself, and
 * an unverified JWT accepted on this side would be a way to sign in as anybody.
 * On success the pair it answers is adopted as the session, so the caller only
 * has to refresh and navigate.
 */
export async function completeSsoSignIn(
  orgSlug: string,
  token: string,
): Promise<SsoSession> {
  const session = await platformRequest<SsoSession>("/api/v1/auth/sso/callback", {
    method: "POST",
    body: { org_slug: orgSlug, token },
  });
  rememberPlatformSession({
    access_token: session.access_token,
    refresh_token: session.refresh_token,
    expires_in: session.expires_in,
  });
  return session;
}

/* ---------- the orthopaedic CV ---------- */

export type StructuredCv = components["schemas"]["StructuredCv"];
export type CvRead = components["schemas"]["CvRead"];

/** Your own CVs, most recent first, with whatever has been read so far. */
export function listCvs(signal?: AbortSignal): Promise<components["schemas"]["CvList"]> {
  return platformRequest<components["schemas"]["CvList"]>("/api/v1/cv", { signal });
}

/**
 * One CV by id.
 *
 * This is what an upload waits on. `POST /cv` answers a row and a status and the
 * sections arrive later from a background job, so the thing being watched is
 * exactly one known record — and re-listing the whole set every five seconds to
 * ask about it is both the slower question and the one that can answer about a
 * different row if a second upload lands in between.
 */
export function readCv(cvId: string, signal?: AbortSignal): Promise<CvRead> {
  return platformRequest<CvRead>(`/api/v1/cv/${encodeURIComponent(cvId)}`, { signal });
}

/**
 * Throw your own CV away, including one still being read.
 *
 * The server answers 204 and nothing else, and somebody else's cv comes back as
 * `cv_not_found` rather than `forbidden` — the same answer a read gives, so a
 * delete cannot be used to find out whose ids exist.
 */
export function deleteCv(cvId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/cv/${encodeURIComponent(cvId)}`, { method: "DELETE" });
}

/**
 * Send a CV for reading.
 *
 * The answer is a row, not a parsed CV: the text is pulled from the PDF in the
 * route and the structuring is a background job, so `status` says `processing`
 * and the sections arrive on the next read. The upload is rate limited because
 * each one buys a model call.
 */
export function uploadCv(file: File): Promise<components["schemas"]["CvUploadResult"]> {
  const form = new FormData();
  // The field name is the backend's parameter name, `file` — the retiring
  // client's Flask route took `cv`, and copying that here would 422.
  form.append("file", file);
  return platformRequest<components["schemas"]["CvUploadResult"]>("/api/v1/cv", {
    method: "POST",
    formData: form,
  });
}
