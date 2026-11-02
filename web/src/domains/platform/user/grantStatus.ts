import type { PlatformEntitlement } from "@/domains/platform/support/api";
import { formatDay } from "@/domains/platform/support";

/** What a grant is to the person today, in the words support uses. */
export type GrantState = "live" | "queued" | "ended" | "revoked";

/** Whether the grant is live now, waiting to start, finished, or withdrawn. */
export function grantState(grant: PlatformEntitlement, now: Date): GrantState {
  if (grant.revoked_at) return "revoked";
  if (new Date(grant.starts_at) > now) return "queued";
  if (grant.ends_at && new Date(grant.ends_at) <= now) return "ended";
  return "live";
}

/** Where a grant came from, in plain words. The raw reference stays in the row's hover text. */
export function sourceLabel(grant: PlatformEntitlement): string {
  if (grant.source === "purchase") {
    return grant.source_ref?.startsWith("legacy-import")
      ? "Purchase (imported from the old site)"
      : "Purchase";
  }
  if (grant.source === "admin") return "Admin grant";
  if (grant.source === "org_grant") return "Organisation seat";
  if (grant.source === "sso_tenant") return "Organisation sign-in";
  return grant.source === "trial" ? "Free trial" : grant.source;
}

/**
 * Whether another grant for the same exam already covers every day of this live one, so removing
 * this one would change nothing today. Only the later-ending grant is ever the "covering" one, so
 * two identical grants are never both marked as covered.
 */
export function coveredByAnother(
  grant: PlatformEntitlement,
  all: PlatformEntitlement[],
  now: Date,
): boolean {
  if (grantState(grant, now) !== "live") return false;
  return all.some((other) => {
    if (other.id === grant.id || other.exam_code !== grant.exam_code) return false;
    if (grantState(other, now) !== "live") return false;
    if (other.ends_at === null) return grant.ends_at !== null;
    if (grant.ends_at === null) return false;
    return new Date(other.ends_at) > new Date(grant.ends_at);
  });
}

/**
 * The first day the person has no access for this exam, counting grants that start later and
 * join on to the current one. `undefined` when they have none today, `null` when it never ends.
 */
export function accessUntil(
  grants: PlatformEntitlement[],
  examCode: string,
  now: Date,
): Date | null | undefined {
  const usable = grants.filter(
    (grant) => grant.exam_code === examCode && grantState(grant, now) !== "revoked",
  );
  let cursor = now;
  let extended = false;
  for (;;) {
    const joining = usable.filter(
      (grant) =>
        new Date(grant.starts_at) <= cursor && (grant.ends_at === null || new Date(grant.ends_at) > cursor),
    );
    if (joining.length === 0) return extended ? cursor : undefined;
    if (joining.some((grant) => grant.ends_at === null)) return null;
    cursor = new Date(Math.max(...joining.map((grant) => new Date(grant.ends_at as string).getTime())));
    extended = true;
  }
}

/** One sentence answering "until when can they practise?", one clause per exam. */
export function accessSummary(grants: PlatformEntitlement[], now: Date): string {
  const exams = [...new Set(grants.map((grant) => grant.exam_code))];
  const clauses = exams.map((examCode) => {
    const until = accessUntil(grants, examCode, now);
    if (until === undefined) return `${examCode}: no access today`;
    return until === null
      ? `${examCode}: open-ended`
      : `${examCode}: access until ${formatDay(until.toISOString())}`;
  });
  return clauses.join(" · ");
}
