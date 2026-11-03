import type { PlatformAccessGrant, PlatformExamAccess, PlatformPlan } from "@/domains/platform/support/api";
import { formatDay } from "@/domains/platform/support/vocabulary";
import { formatMoney } from "@/foundation/format";
import { amountPaidLabel } from "@/domains/platform/support/money";

/** What a grant is to the person today, in the words support uses. */
export type GrantState = "live" | "starts_later" | "ended" | "revoked";

/** Whether a grant is running now, waits to start, has finished or was withdrawn. */
export function grantState(grant: PlatformAccessGrant, now: Date): GrantState {
  if (grant.revoked_at) return "revoked";
  if (grant.live) return "live";
  return new Date(grant.starts_at) > now ? "starts_later" : "ended";
}

/** The badge words for a grant state. */
export const GRANT_STATE_LABEL: Record<GrantState, string> = {
  live: "Live",
  starts_later: "Starts later",
  ended: "Ended",
  revoked: "Revoked",
};

/** Where a grant came from, in plain words. */
export function sourceLabel(source: string): string {
  if (source === "purchase") return "Purchase";
  if (source === "admin") return "Given by staff";
  if (source === "org_grant") return "Organisation seat";
  if (source === "sso_tenant") return "Organisation sign-in";
  return source === "trial" ? "Free trial" : source;
}

/** "6-month plan" for whole months of 30 days, otherwise "45-day plan". */
export function planDurationLabel(durationDays: number): string {
  const months = durationDays / 30;
  return Number.isInteger(months) && months >= 1 ? `${months}-month plan` : `${durationDays}-day plan`;
}

/** A plan as staff would say it, such as "SCA 6-month plan", instead of its code. */
export function planName(plan: Pick<PlatformPlan, "exam_code" | "duration_days">): string {
  return `${plan.exam_code.toUpperCase()} ${planDurationLabel(plan.duration_days)}`;
}

/**
 * One line answering "what can they use for this exam?". `durationDaysByPlan` maps a plan code to
 * its length so the line can say "6-month plan"; an unknown plan falls back to its code.
 */
export function accessLine(row: PlatformExamAccess, durationDaysByPlan: Map<string, number>): string {
  const exam = row.exam_code.toUpperCase();
  const [kind, detail] = row.limit_reason.split(":");
  if (kind === "no_access") return `${exam}: No access`;
  if (kind === "unlimited") {
    return `${exam}: Unlimited because of ${detail === "org_grant" || detail === "sso_tenant" ? "an organisation grant" : "a staff grant or free trial"}`;
  }
  const days = durationDaysByPlan.get(detail ?? "");
  const plan = days === undefined ? `plan ${detail}` : planDurationLabel(days);
  if (row.station_limit === null) return `${exam}: ${plan}. ${row.stations_sat} stations used.`;
  const left = Math.max(row.station_limit - row.stations_sat, 0);
  return `${exam}: ${plan}. ${row.stations_sat} of ${row.station_limit} stations used, ${left} left.`;
}

/**
 * What a bought grant cost, said under the grant: "£24.99 paid 3 Nov 2026 · receipt RCP-sca-1".
 * A free place says so, and a grant that was never bought (staff, organisation, trial) has no line.
 */
export function grantPaymentLine(grant: PlatformAccessGrant): string | null {
  if (grant.amount_total_pence === null || grant.amount_total_pence === undefined) return null;
  const receipt = grant.receipt_id ? `receipt ${grant.receipt_id}` : "no receipt";
  if (grant.amount_total_pence === 0) return `Free place given ${formatDay(grant.paid_at)} · ${receipt}`;
  const money = formatMoney(grant.amount_total_pence, grant.currency ?? "GBP");
  return `${money} paid ${formatDay(grant.paid_at)} · ${receipt}`;
}

/**
 * Whether "when it starts" is a real choice: only when they already hold, or are queued for, a
 * bought plan on this exam. Otherwise a new plan can only start now, so the question is not asked.
 */
export function hasPlanToQueueBehind(row: PlatformExamAccess | undefined, now: Date): boolean {
  if (!row) return false;
  return row.grants.some((grant) => {
    if (grant.source !== "purchase") return false;
    const state = grantState(grant, now);
    return state === "live" || state === "starts_later";
  });
}

/** The give-access button says exactly what pressing it does: "Give SCA 1-month plan for £24.99". */
export function giveAccessLabel(plan: Pick<PlatformPlan, "exam_code" | "duration_days">, pence: number | null): string {
  const price = amountPaidLabel(pence);
  return `Give ${planName(plan)} ${price === "free" ? "for free" : `for ${price}`}`;
}
