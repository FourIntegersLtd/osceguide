/**
 * The support half of the staff console: what happened to one person, and
 * what the console may do about it.
 *
 * Every function here is a `/api/v1/platform/…` route and every one of them
 * is `PlatformAdmin` on the backend. They are the answers to the tickets
 * support actually gets — "I did the station and got no feedback", "I paid
 * and nothing happened", "I cannot sign in" — and the levers that fix them:
 * re-queue the marking, salvage a transcript, grant or revoke access, replay a
 * refused payment, record one that skipped Stripe.
 *
 * Kept apart from `api.ts`, which is the organisation directory: that file is
 * about tenants, this one is about people and their attempts.
 */
import { platformRequest, type components } from "@/foundation/platform-client";
import type { PageParams } from "@/domains/platform/api";

type S = components["schemas"];

export type PlatformAttempt = S["PlatformAttemptRead"];
export type PlatformAttemptDetail = S["PlatformAttemptDetail"];
export type ScoringJob = S["ScoringJobRead"];
export type RescoreResult = S["RescoreResult"];
export type PlatformEntitlement = S["PlatformEntitlementRead"];
export type PlatformPayment = S["PlatformPaymentRead"];
export type StripeEvent = S["StripeEventRead"];
export type PlatformAuditEntry = S["PlatformAuditRead"];
export type OrgAtRisk = S["OrgAtRisk"];
export type Job = S["JobRead"];
export type JobsPage = S["JobsPage"];
export type PlatformHealth = S["PlatformHealth"];
export type CloudCapacity = S["CloudCapacityRead"];

interface Page<T> {
  items: T[];
  next_cursor?: string | null;
}

const PLATFORM = "/api/v1/platform";
const user = (id: string) => `${PLATFORM}/users/${encodeURIComponent(id)}`;
const attempt = (id: string) => `${PLATFORM}/attempts/${encodeURIComponent(id)}`;
const entitlement = (id: string) => `${PLATFORM}/entitlements/${encodeURIComponent(id)}`;

function pageQuery(page?: PageParams) {
  return { limit: page?.limit ?? 25, cursor: page?.cursor ?? undefined };
}

/* --------------------------------------------------------------- Attempts */

/** One person's attempts, newest first, each saying whether its transcript
 *  arrived, whether it was marked, and what the queue holds for it. */
export function listUserAttempts(
  userId: string,
  options: { status?: string | null } & PageParams = {},
  signal?: AbortSignal,
): Promise<Page<PlatformAttempt>> {
  return platformRequest<Page<PlatformAttempt>>(`${user(userId)}/attempts`, {
    signal,
    query: { ...pageQuery(options), status: options.status ?? undefined },
  });
}

export function readAttemptForSupport(
  attemptId: string,
  signal?: AbortSignal,
): Promise<PlatformAttemptDetail> {
  return platformRequest<PlatformAttemptDetail>(attempt(attemptId), { signal });
}

/** Queue the marking again. Twice is once; an existing result is kept. */
export function rescoreAttempt(
  attemptId: string,
  policyVersion?: string | null,
): Promise<RescoreResult> {
  return platformRequest<RescoreResult>(`${attempt(attemptId)}/rescore`, {
    method: "POST",
    body: { policy_version: policyVersion || null },
  });
}

/** Treat the turns that arrived as the transcript the worker never delivered. */
export function salvageAttempt(attemptId: string): Promise<PlatformAttemptDetail> {
  return platformRequest<PlatformAttemptDetail>(`${attempt(attemptId)}/salvage`, {
    method: "POST",
  });
}

/** End a stuck attempt so the person, or their supervisor, can start a fresh one. */
export function failAttempt(attemptId: string, reason: string): Promise<PlatformAttemptDetail> {
  return platformRequest<PlatformAttemptDetail>(`${attempt(attemptId)}/fail`, {
    method: "POST",
    body: { reason },
  });
}

/* ----------------------------------------------------------- Entitlements */

export function listUserEntitlements(
  userId: string,
  signal?: AbortSignal,
): Promise<Page<PlatformEntitlement>> {
  return platformRequest<Page<PlatformEntitlement>>(`${user(userId)}/entitlements`, { signal });
}

/** Grant access outright, source `admin`, with the reason in the audit log. */
export function grantEntitlement(
  userId: string,
  input: { examCode: string; endsAt?: string | null; note: string },
): Promise<PlatformEntitlement> {
  return platformRequest<PlatformEntitlement>(`${user(userId)}/entitlements`, {
    method: "POST",
    body: { exam_code: input.examCode, ends_at: input.endsAt ?? null, note: input.note },
  });
}

/** Move the end date. A renewal is this rather than a second row. */
export function extendEntitlement(
  entitlementId: string,
  input: { endsAt: string | null; note?: string | null },
): Promise<PlatformEntitlement> {
  return platformRequest<PlatformEntitlement>(entitlement(entitlementId), {
    method: "PATCH",
    body: { ends_at: input.endsAt, note: input.note ?? null },
  });
}

export function revokeEntitlement(
  entitlementId: string,
  reason: string,
): Promise<PlatformEntitlement> {
  return platformRequest<PlatformEntitlement>(`${entitlement(entitlementId)}/revoke`, {
    method: "POST",
    body: { reason },
  });
}

/* ---------------------------------------------------------------- Billing */

export function listUserPayments(
  userId: string,
  signal?: AbortSignal,
): Promise<Page<PlatformPayment>> {
  return platformRequest<Page<PlatformPayment>>(`${user(userId)}/payments`, { signal });
}

/** Every webhook delivery naming this person's address, applied or refused. */
export function listUserBillingEvents(
  userId: string,
  signal?: AbortSignal,
): Promise<Page<StripeEvent>> {
  return platformRequest<Page<StripeEvent>>(`${user(userId)}/billing-events`, { signal });
}

/** The webhook ledger, newest first. `failedOnly` is the reconcile queue. */
export function listBillingEvents(
  options: { failedOnly?: boolean } & PageParams = {},
  signal?: AbortSignal,
): Promise<Page<StripeEvent>> {
  return platformRequest<Page<StripeEvent>>(`${PLATFORM}/billing/events`, {
    signal,
    query: { ...pageQuery(options), failed_only: options.failedOnly ? true : undefined },
  });
}

/** Apply a refused delivery again, once its cause is fixed. */
export function replayBillingEvent(eventId: string): Promise<{ status: string }> {
  return platformRequest<{ status: string }>(
    `${PLATFORM}/billing/events/${encodeURIComponent(eventId)}/replay`,
    { method: "POST" },
  );
}

/** A payment that did not come through Stripe, recorded so it grants like one that did. */
export function recordManualPayment(
  userId: string,
  input: {
    planCode: string;
    reference?: string | null;
    amountPence?: number | null;
    paidAt?: string | null;
    note: string;
  },
): Promise<PlatformPayment> {
  return platformRequest<PlatformPayment>(`${user(userId)}/payments`, {
    method: "POST",
    body: {
      plan_code: input.planCode,
      stripe_payment_intent_id: input.reference || null,
      amount_total_pence: input.amountPence ?? null,
      paid_at: input.paidAt ?? null,
      note: input.note,
    },
  });
}

/** Record-only: the money moves in Stripe; this withdraws what it bought. */
export function recordRefund(paymentId: string, reason: string): Promise<PlatformPayment> {
  return platformRequest<PlatformPayment>(
    `${PLATFORM}/payments/${encodeURIComponent(paymentId)}/refund`,
    { method: "POST", body: { reason } },
  );
}

/* ------------------------------------------------------------------ Audit */

export function listPlatformAudit(
  options: { orgSlug?: string | null; actorEmail?: string | null; action?: string | null } & PageParams = {},
  signal?: AbortSignal,
): Promise<Page<PlatformAuditEntry>> {
  return platformRequest<Page<PlatformAuditEntry>>(`${PLATFORM}/audit`, {
    signal,
    query: {
      ...pageQuery(options),
      org_slug: options.orgSlug?.trim() || undefined,
      actor_email: options.actorEmail?.trim() || undefined,
      action: options.action?.trim() || undefined,
    },
  });
}

/** Everything done to this account and everything it did, newest first. */
export function listUserAudit(
  userId: string,
  page?: PageParams,
  signal?: AbortSignal,
): Promise<Page<PlatformAuditEntry>> {
  return platformRequest<Page<PlatformAuditEntry>>(`${user(userId)}/audit`, {
    signal,
    query: pageQuery(page),
  });
}

/* ------------------------------------------------------------ Organisation */

/** New dates and, unless told otherwise, the suspension lifted with them. */
export function renewContract(
  slug: string,
  input: { endsAt: string; startsAt?: string | null; restore?: boolean },
): Promise<S["OrganizationRead"]> {
  return platformRequest<S["OrganizationRead"]>(
    `${PLATFORM}/organizations/${encodeURIComponent(slug)}/contract`,
    {
      method: "POST",
      body: {
        contract_ends_at: input.endsAt,
        contract_starts_at: input.startsAt ?? null,
        restore: input.restore ?? true,
      },
    },
  );
}

type Membership = S["app__features__tenancy__schemas__MembershipRead"];

const membership = (slug: string, id: string) =>
  `${PLATFORM}/organizations/${encodeURIComponent(slug)}/memberships/${encodeURIComponent(id)}`;

export function changeMembershipRole(slug: string, membershipId: string, role: string): Promise<Membership> {
  return platformRequest<Membership>(membership(slug, membershipId), { method: "PATCH", body: { role } });
}

export function revokeMembership(slug: string, membershipId: string): Promise<Membership> {
  return platformRequest<Membership>(`${membership(slug, membershipId)}/revoke`, { method: "POST" });
}

export function restoreMembership(slug: string, membershipId: string): Promise<Membership> {
  return platformRequest<Membership>(`${membership(slug, membershipId)}/restore`, { method: "POST" });
}

/* -------------------------------------------------------------------- Ops */

export function readPlatformHealth(signal?: AbortSignal): Promise<PlatformHealth> {
  return platformRequest<PlatformHealth>(`${PLATFORM}/health`, { signal });
}

export function listJobs(
  options: { status?: string | null; task?: string | null; beforeId?: number | null; limit?: number } = {},
  signal?: AbortSignal,
): Promise<JobsPage> {
  return platformRequest<JobsPage>(`${PLATFORM}/jobs`, {
    signal,
    query: {
      status: options.status || undefined,
      task: options.task?.trim() || undefined,
      before_id: options.beforeId ?? undefined,
      limit: options.limit ?? 50,
    },
  });
}

export function readCloudCapacity(signal?: AbortSignal): Promise<CloudCapacity> {
  return platformRequest<CloudCapacity>(`${PLATFORM}/voice/capacity`, { signal });
}
