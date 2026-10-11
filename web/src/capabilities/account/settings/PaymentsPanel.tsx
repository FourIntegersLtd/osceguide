"use client";

import { useEffect } from "react";
import { HiOutlineBuildingOffice2, HiOutlineClock, HiOutlineCreditCard, HiOutlineSparkles } from "react-icons/hi2";
import { AsyncBoundary, productTokens, Panel } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { listEntitlements, listPlans, listReceipts, type Receipt } from "@/capabilities/account/api";
import { currentPlanView, type CurrentPlanView } from "@/capabilities/account/access";
import PlanPicker, { UPGRADE_LEAD } from "@/capabilities/account/settings/PlanPicker";
import { plansForAccount } from "@/capabilities/account/settings/plansForAccount";
import { SUPPORT_EMAIL } from "@/foundation/support";
import ReceiptList from "@/capabilities/account/settings/ReceiptList";
import { SettingsRow, SettingsRows, StatusPill, settingsSub } from "@/capabilities/account/settings/SettingsKit";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";
import { B2CHero } from "@/foundation/ui/B2CHero";

const { b2cLink } = productTokens;

/** What full access gives. The product has no courses, so this never mentions any. */
const FULL_ACCESS =
  "Full access includes every practice station, the whole study library (A to Z summaries, slides and podcasts), debriefs with Athena and practice with colleagues";

const PLAN_ICON = {
  free: HiOutlineSparkles,
  trial: HiOutlineClock,
  paid: HiOutlineCreditCard,
  organisation: HiOutlineBuildingOffice2,
} as const;

/**
 * Your plan: what you hold now, the one-off plans you can buy, and your receipts.
 *
 * Access is fixed-term and paid once (`mode=payment`): nothing renews, so there
 * is no subscription to manage. "Current plan" is `currentPlanView` over the
 * live entitlements, the trial allowance and the newest receipt. A live grant
 * is `live === true` and nothing else: `/me/entitlements` returns revoked and
 * expired rows too.
 *
 * Entitlements and receipts load together so a failure is an error and never
 * falls through to the plans: a paying person must not be asked to pay again
 * because of a network blip. Checkout opens in a new tab, so both are read
 * again when this tab is shown again and the plan updates on return.
 */
export default function PaymentsPanel() {
  const state = useAsync(async (signal) => {
    const [entitlements, receipts] = await Promise.all([listEntitlements(signal), listReceipts(signal)]);
    return { plan: currentPlanView(entitlements, new Date()), receipts };
  }, []);
  const { reload } = state;

  useEffect(() => {
    const onShow = () => {
      if (document.visibilityState === "visible") reload();
    };
    document.addEventListener("visibilitychange", onShow);
    return () => document.removeEventListener("visibilitychange", onShow);
  }, [reload]);

  return (
    <SettingsTabShell>
      <B2CHero title="Your plan">{FULL_ACCESS}</B2CHero>
      <AsyncBoundary state={state}>
        {({ plan, receipts }) => (
          <>
            <CurrentPlan plan={plan} />
            {plan.upgrade ? <Upgrade /> : null}
            <Receipts receipts={receipts} paid={plan.kind === "paid"} />
          </>
        )}
      </AsyncBoundary>
    </SettingsTabShell>
  );
}

function CurrentPlan({ plan }: { plan: CurrentPlanView }) {
  return (
    <Panel title="Current plan">
      <SettingsRows>
        <SettingsRow
          icon={PLAN_ICON[plan.kind]}
          title={plan.title}
          meta={plan.meta}
          trailing={plan.active ? <StatusPill tone="ok">Active</StatusPill> : null}
        />
      </SettingsRows>
    </Panel>
  );
}

/**
 * The plans this person may buy: the exam their account holds on the server, only (`plansForAccount`).
 *
 * The exam is chosen at sign-up and moving somebody is a support action, so
 * listing PLAB and ORTHO beside SCA sold an SCA account a library every other
 * screen hides; checkout refuses those plans too (`billing/service_checkout.py`).
 * With no exam yet, every plan is on offer, because what they buy becomes it.
 * Somebody with a running purchase may buy a different plan; it starts where
 * the running access ends.
 */
function Upgrade() {
  const plans = useAsync((signal) => listPlans(signal), []);
  const { session } = useSession();
  const examCode = session?.user.exam_code ?? null;

  return (
    <Panel title="Upgrade" description={UPGRADE_LEAD}>
      <AsyncBoundary state={plans}>
        {(page) => {
          const onSale = plansForAccount(page.items, examCode);
          // Keyed by exam so a changed exam resets the selected plan.
          return onSale.length > 0 ? (
            <PlanPicker key={examCode ?? "any"} plans={onSale} />
          ) : (
            <p className={settingsSub}>
              There are no plans on sale at the moment. Get in touch and we will set your access up.
            </p>
          );
        }}
      </AsyncBoundary>
    </Panel>
  );
}

function Receipts({ receipts, paid }: { receipts: Receipt[]; paid: boolean }) {
  if (receipts.length > 0) {
    return (
      <Panel title="Receipts">
        <ReceiptList receipts={receipts} />
      </Panel>
    );
  }
  if (!paid) return null;
  return (
    <p className={settingsSub}>
      Receipt unavailable.{" "}
      <a href={`mailto:${SUPPORT_EMAIL}`} className={b2cLink}>
        Contact support
      </a>{" "}
      if you need confirmation.
    </p>
  );
}
