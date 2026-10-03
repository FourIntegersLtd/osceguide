import type { Entitlement } from "@/capabilities/account/api";

/**
 * Access this person holds beyond a trial: bought, or given by an
 * organisation, an institution or the team.
 *
 * A grant is `live === true` and nothing else: `/me/entitlements` answers with
 * revoked and expired rows too. A trial is live but is what the plans are for,
 * so somebody inside one is still offered them.
 *
 * The exam the account was opened for (`exam_codes` on `/me/dashboard`) is not
 * access: reading it as "paid" hid "Upgrade to Pro" from every free account
 * the moment it chose an exam.
 */
export function paidAccess(entitlements: readonly Entitlement[]): Entitlement[] {
  return entitlements.filter((entitlement) => entitlement.live && entitlement.source !== "trial");
}

/** Whether `paidAccess` covers this exam; with no exam chosen yet, any exam. */
export function holdsPaidAccess(
  entitlements: readonly Entitlement[],
  examCode: string | null,
): boolean {
  return paidAccess(entitlements).some(
    (entitlement) => examCode === null || entitlement.exam_code === examCode,
  );
}
