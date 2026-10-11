import { formatLongDate } from "@/foundation/format";
import type { Entitlement, MyEntitlements } from "@/capabilities/account/api";

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
export function paidAccess<T extends Entitlement>(entitlements: readonly T[]): T[] {
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

/**
 * When the live access ends: the latest end among live grants, or null when none is live or any is
 * open-ended (open-ended outlasts every date).
 */
export function latestLiveEnd(entitlements: readonly Entitlement[]): string | null {
  const live = entitlements.filter((entitlement) => entitlement.live);
  const ends = live.flatMap((entitlement) => (entitlement.ends_at === null ? [] : [entitlement.ends_at]));
  if (ends.length === 0 || ends.length < live.length) return null;
  return ends.reduce((latest, value) => (new Date(value) > new Date(latest) ? value : latest));
}

const DAY_MS = 24 * 60 * 60 * 1000;

/** The Payments tab's "Current plan" row. */
export interface CurrentPlanView {
  kind: "free" | "trial" | "paid" | "organisation";
  title: string;
  meta: string;
  /** Live access of any kind: the row carries the Active pill. */
  active: boolean;
  /** Whether the plans are offered. An organisation's grant is not sent to checkout. */
  upgrade: boolean;
}

/**
 * What this person holds now, in one line: a purchase, else access somebody gave them, else a
 * running trial, else nothing (with what the free trial allows, from the server).
 *
 * A purchase reads its live grants, never the newest receipt: that can be a plan queued after the
 * running one, or a refunded one. It started when the earliest live purchase did and ends when the
 * last one does. A trial's days are counted against `now` (a parameter so tests can pin it), and one
 * that ends later today still reads "1 day left". Access that has run out says so: the trial's
 * station allowance is not on offer to somebody who has already used it.
 */
export function currentPlanView(
  entitlements: MyEntitlements,
  now: Date,
): CurrentPlanView {
  const paid = paidAccess(entitlements.items);
  const purchases = paid.filter((entitlement) => entitlement.source === "purchase");
  const ends = (live: readonly Entitlement[]) => {
    const end = latestLiveEnd(live);
    return end ? `Ends ${formatLongDate(end)}` : "No end date";
  };

  if (purchases.length > 0) {
    const started = purchases.reduce((earliest, entitlement) =>
      new Date(entitlement.starts_at) < new Date(earliest.starts_at) ? entitlement : earliest,
    ).starts_at;
    const end = latestLiveEnd(purchases);
    return {
      kind: "paid",
      title: "Full access",
      meta: `Started ${formatLongDate(started)}, ${end ? `ends ${formatLongDate(end)}` : "no end date"}`,
      active: true,
      upgrade: true,
    };
  }
  const [given] = paid;
  if (given) {
    return { kind: "organisation", title: grantLabel(given.source), meta: ends(paid), active: true, upgrade: false };
  }

  const trial = entitlements.items.find(
    (entitlement) => entitlement.live && entitlement.source === "trial" && entitlement.ends_at !== null,
  );
  if (trial?.ends_at) {
    const days = Math.max(1, Math.ceil((new Date(trial.ends_at).getTime() - now.getTime()) / DAY_MS));
    return {
      kind: "trial",
      title: `Free trial, ${days === 1 ? "1 day" : `${days} days`} left`,
      meta: `Ends ${formatLongDate(trial.ends_at)}`,
      active: true,
      upgrade: true,
    };
  }

  const stations = entitlements.trial.stations;
  const ran = (trial: boolean) => entitlements.items.some((e) => !e.live && (e.source === "trial") === trial);
  return {
    kind: "free",
    title: "Free",
    meta: ran(false)
      ? "Your access has ended"
      : ran(true)
        ? "Your free trial has ended"
        : `You can try ${stations === 1 ? "1 station" : `${stations} stations`}`,
    active: false,
    upgrade: true,
  };
}

/**
 * The title for access nobody paid for here. `org_grant`, `sso_tenant` and `admin` are the
 * backend's own spelling (`entitlements/domain.py`); a raw value once read "From Your Org_grant".
 */
function grantLabel(source: string): string {
  if (source === "org_grant" || source === "sso_tenant") return "Organisation access";
  if (source === "admin") return "Access from the OSCE Guide team";
  return source.replace(/_/g, " ");
}
