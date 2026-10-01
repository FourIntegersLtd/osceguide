"use client";

import {
  AsyncBoundary,
  ModalHelper,
  Panel,
  productTokens,
} from "@/foundation/ui";
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
import PlanPicker, { SUPPORT_EMAIL } from "@/capabilities/account/settings/PlanPicker";
import ReceiptList from "@/capabilities/account/settings/ReceiptList";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

const { b2cFieldLabel, b2cFieldValue, b2cLink } = productTokens;

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
      const live = entitlements.items.filter(
        (entitlement) => entitlement.live && entitlement.source !== "trial",
      );
      return { live, receipts };
    },
    [],
  );

  return (
    <SettingsTabShell>
      <AsyncBoundary state={state}>
        {({ live, receipts }) => (
          <Panel title="Payments" className="overflow-hidden">
            <div className="space-y-5">
              {live.length > 0 ? (
                <ActivePlan live={live} receipts={receipts} />
              ) : (
                <Plans />
              )}
            </div>
          </Panel>
        )}
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

  const rows: { label: string; value: string }[] = [
    { label: "Plan", value: plan },
    ...(latest?.plan_start_date ? [{ label: "Started", value: latest.plan_start_date }] : []),
    ...(endsAt ? [{ label: "Valid until", value: formatLongDate(endsAt) }] : []),
  ];
  const purchased = live.some((entitlement) => entitlement.source === "purchase");

  return (
    <>
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-osce-body font-semibold text-ink">Premium</p>
          <span className="inline-flex items-center gap-1.5 text-osce-meta font-medium text-osce-success-text">
            <span className="h-1.5 w-1.5 rounded-full bg-osce-success-icon" aria-hidden />
            Active
          </span>
        </div>
        <ModalHelper className="mt-1">
          {endsAt
            ? `Full access until ${formatLongDate(endsAt)}.`
            : "You have full access to all premium features."}
        </ModalHelper>
      </div>

      <dl className="divide-y divide-border rounded-xl border border-border">
        {rows.map((row) => (
          <div key={row.label} className="flex items-center justify-between gap-4 px-4 py-3">
            <dt className={b2cFieldLabel}>{row.label}</dt>
            <dd className={`${b2cFieldValue} text-right`}>{row.value}</dd>
          </div>
        ))}
      </dl>

      {receipts.length > 0 ? (
        <ReceiptList receipts={receipts} />
      ) : purchased ? (
        <ModalHelper className="mt-0">
          Receipt unavailable.{" "}
          <a href={`mailto:${SUPPORT_EMAIL}`} className={b2cLink}>
            Contact support
          </a>{" "}
          if you need confirmation.
        </ModalHelper>
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
function Plans() {
  const plans = useAsync((signal) => listPlans(signal), []);
  const exam = useCurrentExam();

  return (
    <AsyncBoundary state={plans}>
      {(page) => {
        // Wait for the exam rather than flash every exam's plans first.
        if (exam.loading) return null;
        const onSale = plansForExam(page.items, exam.code);
        if (onSale.length === 0) {
          return (
            <ModalHelper className="mt-0">
              There are no plans on sale at the moment. Get in touch and we will set your access up.
            </ModalHelper>
          );
        }
        // Keyed by exam so switching exams resets the selected plan.
        return <PlanPicker key={exam.code ?? "any"} plans={onSale} />;
      }}
    </AsyncBoundary>
  );
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
