"use client";

import { HiOutlineBuildingOffice2, HiOutlineClock, HiOutlineCreditCard } from "react-icons/hi2";
import { AsyncBoundary, productTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { formatLongDate } from "@/foundation/format";
import { useCurrentExam } from "@/foundation/session";
import {
  listEntitlements,
  listPlans,
  listReceipts,
  type Entitlement,
  type Plan,
  type Receipt,
} from "@/capabilities/account/api";
import { paidAccess } from "@/capabilities/account/access";
import PlanPicker, { SUPPORT_EMAIL } from "@/capabilities/account/settings/PlanPicker";
import ReceiptList from "@/capabilities/account/settings/ReceiptList";
import {
  DotEyebrow,
  SettingsCard,
  SettingsRow,
  SettingsRows,
  StatusPill,
  settingsSub,
} from "@/capabilities/account/settings/SettingsKit";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";
import { B2CHero } from "@/foundation/ui/B2CHero";

const { b2cLink } = productTokens;

const DAY_MS = 24 * 60 * 60 * 1000;

/** A free trial still running: when it ends, and the whole days left as the page loaded. */
interface Trial {
  endsAt: string;
  daysLeft: number;
}

/**
 * The retiring client's Payments tab: one "Payments" card.
 *
 * With live access it says so — Premium, until when, the plan and its
 * receipt. Without it, it is the plan picker and nothing else, as the old
 * `PaymentsUpgrade` was. The old screen switched on a
 * `has_paid` flag; here the switch is a live entitlement, because an
 * institution's grant is access too and must not be offered a checkout.
 *
 * A live grant is `live === true` and nothing else. `list_for_user` returns
 * revoked and expired rows too, and reading the list as "what I have" is how a
 * revoked entitlement went on unlocking stations.
 *
 * Entitlements and receipts load together so a failure is an error and never
 * falls through to the plans: a paying person must not be asked to pay again
 * because of a network blip.
 */
export default function PaymentsPanel() {
  const state = useAsync(
    async (signal) => {
      const [entitlements, receipts] = await Promise.all([
        listEntitlements(signal),
        listReceipts(signal),
      ]);
      // A trial is live too, but it is what the plans are for: somebody still
      // inside it is offered them, as the old screen's `has_paid` flag did.
      return {
        live: paidAccess(entitlements.items),
        trial: runningTrial(entitlements.items),
        receipts,
      };
    },
    [],
  );

  return (
    <SettingsTabShell>
      <AsyncBoundary state={state}>
        {({ live, trial, receipts }) =>
          live.length > 0 ? <ActivePlan live={live} receipts={receipts} /> : <Plans trial={trial} />
        }
      </AsyncBoundary>
    </SettingsTabShell>
  );
}

/**
 * Premium, active, and the facts behind it.
 *
 * The plan and start date come from the newest receipt, which is the purchase
 * that set the access up; "Valid until" is the latest end among live grants,
 * so two grants for one exam (a purchase and its renewal) read as one line
 * rather than two. A grant with no end date means open-ended access.
 */
function ActivePlan({ live, receipts }: { live: Entitlement[]; receipts: Receipt[] }) {
  const latest = receipts[0] ?? null;
  const openEnded = live.some((entitlement) => entitlement.ends_at === null);
  const endsAt = openEnded ? null : latestEnd(live);
  const plan = latest?.plan_label ?? grantLabel(live);

  const purchased = live.some((entitlement) => entitlement.source === "purchase");
  const facts = [
    latest?.plan_start_date ? `Started ${latest.plan_start_date}` : null,
    endsAt ? `Valid until ${formatLongDate(endsAt)}` : "No end date",
  ].filter((fact): fact is string => fact !== null);

  return (
    <>
      <B2CHero eyebrow={<DotEyebrow tone="ok">Your plan</DotEyebrow>} title={plan}>
        {endsAt
          ? `Full access until ${formatLongDate(endsAt)}: every station, the study library and debriefs with Athena.`
          : "You have full access: every station, the study library and debriefs with Athena."}
      </B2CHero>

      <SettingsCard title={purchased ? "Your own plan" : "Organisation access"}>
        <SettingsRows>
          <SettingsRow
            icon={purchased ? HiOutlineCreditCard : HiOutlineBuildingOffice2}
            title={plan}
            meta={facts.join(" · ")}
            trailing={<StatusPill tone="ok">Active</StatusPill>}
          />
        </SettingsRows>
      </SettingsCard>

      {receipts.length > 0 ? (
        <SettingsCard title="Receipts">
          <ReceiptList receipts={receipts} />
        </SettingsCard>
      ) : purchased ? (
        <p className={settingsSub}>
          Receipt unavailable.{" "}
          <a href={`mailto:${SUPPORT_EMAIL}`} className={b2cLink}>
            Contact support
          </a>{" "}
          if you need confirmation.
        </p>
      ) : null}
    </>
  );
}

/**
 * The plans this person may buy: their current exam's only.
 *
 * The exam is chosen at sign-up and moving somebody is a support action, so
 * listing PLAB and ORTHO beside SCA sold an SCA account a library every other
 * screen hides; checkout refuses those plans too (`billing/service_checkout.py`).
 * With no exam yet, every plan is on offer, because what they buy becomes it.
 */
function Plans({ trial }: { trial: Trial | null }) {
  const plans = useAsync((signal) => listPlans(signal), []);
  const exam = useCurrentExam();

  return (
    <AsyncBoundary state={plans}>
      {(page) => {
        // Wait for the exam rather than flash every exam's plans first.
        if (exam.loading) return null;
        const onSale = plansForExam(page.items, exam.code);
        const hero = (
          <B2CHero
            eyebrow={<DotEyebrow tone="warning">Your plan</DotEyebrow>}
            title={trial ? `Free trial, ${daysLeftLabel(trial.daysLeft)}` : "Choose a plan"}
          >
            Choose a plan to unlock every station, study material and practice with colleagues.
          </B2CHero>
        );
        if (onSale.length === 0) {
          return (
            <>
              {hero}
              <p className={settingsSub}>
                There are no plans on sale at the moment. Get in touch and we will set your access up.
              </p>
            </>
          );
        }
        // Keyed by exam so switching exams resets the selected plan.
        return (
          <>
            {hero}
            <SettingsCard title="Choose the option that suits you best">
              <PlanPicker key={exam.code ?? "any"} plans={onSale} />
            </SettingsCard>
            {trial ? (
              <SettingsCard title="Receipts">
                <SettingsRows>
                  <SettingsRow
                    icon={HiOutlineClock}
                    title="Free trial"
                    meta={`Ends ${formatLongDate(trial.endsAt)}`}
                    trailing={<StatusPill tone="ok">Active</StatusPill>}
                  />
                </SettingsRows>
              </SettingsCard>
            ) : null}
          </>
        );
      }}
    </AsyncBoundary>
  );
}

/**
 * The trial somebody is still inside, if any.
 *
 * Days are counted here, in the loader, so rendering stays pure; a trial that
 * ends later today still reads "1 day left".
 */
function runningTrial(entitlements: Entitlement[]): Trial | null {
  const trial = entitlements.find(
    (entitlement) => entitlement.live && entitlement.source === "trial" && entitlement.ends_at !== null,
  );
  if (!trial?.ends_at) return null;
  const daysLeft = Math.max(1, Math.ceil((new Date(trial.ends_at).getTime() - Date.now()) / DAY_MS));
  return { endsAt: trial.ends_at, daysLeft };
}

function daysLeftLabel(days: number): string {
  return days === 1 ? "1 day left" : `${days} days left`;
}

function plansForExam(plans: Plan[], examCode: string | null): Plan[] {
  if (examCode === null) return plans;
  return plans.filter((plan) => plan.exam_code === examCode);
}

function latestEnd(live: Entitlement[]): string | null {
  const ends = live
    .map((entitlement) => entitlement.ends_at)
    .filter((value): value is string => value !== null);
  if (ends.length === 0) return null;
  return ends.reduce((latest, value) => (new Date(value) > new Date(latest) ? value : latest));
}

/**
 * The plan line for access nobody paid for here.
 *
 * `org_grant`, `sso_tenant` and the rest are the backend's own spelling
 * (`entitlements/domain.py`). A `capitalize` class over the raw value read
 * "From Your Org_grant".
 */
function grantLabel(live: Entitlement[]): string {
  const named: Record<string, string> = {
    purchase: "Purchased access",
    org_grant: "Access from your organisation",
    sso_tenant: "Access from your institution",
    admin: "Access from the OSCE Guide team",
  };
  const source = live[0]?.source ?? "";
  return named[source] ?? source.replace(/_/g, " ");
}
