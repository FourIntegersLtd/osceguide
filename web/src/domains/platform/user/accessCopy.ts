import type { PlatformAccessGrant, PlatformExamAccess, PlatformPlan } from "@/domains/platform/support/api";

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

/** The words that sit under "Give access", saying exactly when the plan will start. */
export function startChoiceLabel(start: "now" | "after_current"): string {
  return start === "now" ? "starts now" : "starts when the current plan ends";
}
