"use client";

import { HiOutlineCheckCircle, HiOutlineCreditCard } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  ModalHelper,
  productTokens,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import {
  listEntitlements,
  listPlans,
  type Entitlement,
  type Plan,
} from "@/capabilities/account/api";
import PlanPicker from "@/capabilities/account/settings/PlanPicker";
import ReceiptsCard from "@/capabilities/account/settings/ReceiptsCard";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

const { b2cFieldLabel, b2cFieldValue, b2cSettingsCardHeaderIcon } = productTokens;

/**
 * What you can practise, why, and until when — and how to buy more.
 *
 * Two lists rather than one, because a payment does not *mean* access: it
 * granted it. An entitlement carries its source, so "my institution gave me
 * this" and "I bought this" are visibly different things, and a refund revokes
 * the grant while the payment record stands.
 *
 * A live grant is `live === true` and nothing else. `list_for_user` returns
 * revoked and expired rows too, and reading the list as "what I have" is how a
 * revoked entitlement went on unlocking stations.
 *
 * The plans on offer are the current exam's only. The exam is chosen at
 * sign-up and moving somebody is a support action, so listing PLAB and ORTHO
 * beside SCA sold an SCA account a library every other screen hides; checkout
 * refuses those plans too (`billing/service_checkout.py`).
 */
export default function AccessPanel() {
  const entitlements = useAsync((signal) => listEntitlements(signal), []);
  const plans = useAsync((signal) => listPlans(signal), []);
  const exam = useCurrentExam();

  return (
    <SettingsTabShell>
      <AsyncBoundary state={entitlements}>
        {(data) => <EntitlementsCard items={data.items} />}
      </AsyncBoundary>

      <AsyncBoundary state={plans}>
        {(page) => {
          // Wait for the exam rather than flash every exam's plans first.
          if (exam.loading) return null;
          const onSale = plansForExam(page.items, exam.code);
          return (
            <B2CPanelCard className="mt-0 overflow-hidden">
              <B2CPanelCardHeader>
                <HiOutlineCreditCard className={b2cSettingsCardHeaderIcon} aria-hidden />
                Payments
              </B2CPanelCardHeader>
              <B2CPanelCardBody>
                {onSale.length === 0 ? (
                  <ModalHelper className="mt-0">
                    There are no plans on sale at the moment. Get in touch and we will set
                    your access up.
                  </ModalHelper>
                ) : (
                  // Keyed by exam so switching exams resets the selected plan.
                  <PlanPicker key={exam.code ?? "any"} plans={onSale} />
                )}
              </B2CPanelCardBody>
            </B2CPanelCard>
          );
        }}
      </AsyncBoundary>

      <ReceiptsCard />
    </SettingsTabShell>
  );
}

/**
 * The plans this person may buy: their current exam's, or every plan when they
 * have no exam yet, because what they buy then becomes their exam.
 */
function plansForExam(plans: Plan[], examCode: string | null): Plan[] {
  if (examCode === null) return plans;
  return plans.filter((plan) => plan.exam_code === examCode);
}

function EntitlementsCard({ items }: { items: Entitlement[] }) {
  const live = items.filter((entitlement) => entitlement.live);

  return (
    <B2CPanelCard className="mt-0 overflow-hidden">
      <B2CPanelCardHeader>
        <HiOutlineCheckCircle className={b2cSettingsCardHeaderIcon} aria-hidden />
        Active access
      </B2CPanelCardHeader>
      <B2CPanelCardBody className="space-y-4">
        {live.length === 0 ? (
          <ModalHelper className="mt-0">
            You have no access yet. A free trial covers a few stations so you can decide.
          </ModalHelper>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-osce-body font-semibold text-osce-ink-900">Premium</p>
              <span className="inline-flex items-center gap-1.5 text-osce-meta font-medium text-osce-success-text">
                <span
                  className="h-1.5 w-1.5 rounded-full bg-osce-success-icon"
                  aria-hidden
                />
                Active
              </span>
            </div>
            <dl className="divide-y divide-b2c-border rounded-xl border border-b2c-border">
              {live.map((entitlement) => (
                <div
                  key={`${entitlement.exam_code}-${entitlement.source}`}
                  className="flex items-center justify-between gap-4 px-4 py-3"
                >
                  <dt className={b2cFieldLabel}>
                    {entitlement.exam_code.toUpperCase()} · from your{" "}
                    {sourceLabel(entitlement.source)}
                  </dt>
                  <dd className={`${b2cFieldValue} text-right`}>
                    {entitlement.ends_at ? formatDate(entitlement.ends_at) : "No end date"}
                  </dd>
                </div>
              ))}
            </dl>
          </>
        )}
        <EndedList items={items.filter((entitlement) => !entitlement.live)} />
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}

function EndedList({ items }: { items: Entitlement[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className={b2cFieldLabel}>Ended</p>
      <ul className="mt-1.5 space-y-1">
        {items.map((entitlement) => (
          <li
            key={`${entitlement.exam_code}-${entitlement.source}-ended`}
            className="text-osce-meta text-b2c-text-muted"
          >
            {entitlement.exam_code.toUpperCase()} from your {sourceLabel(entitlement.source)}
            {entitlement.ends_at ? ` · ended ${formatDate(entitlement.ends_at)}` : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Where an entitlement came from, in words.
 *
 * `org_grant`, `sso_tenant` and the rest are the backend's own spelling
 * (`entitlements/domain.py`). A `capitalize` class over the raw value read
 * "From Your Org_grant", which is the kind of thing that survives to
 * production because nobody in the team has an org grant on their test
 * account.
 */
function sourceLabel(source: string): string {
  const named: Record<string, string> = {
    purchase: "purchase",
    org_grant: "organisation",
    trial: "free trial",
    sso_tenant: "institution",
    admin: "OSCE Guide team",
  };
  return named[source] ?? source.replace(/_/g, " ");
}

export function formatDate(value: string): string {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "—";
  return date.toLocaleDateString("en-GB", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}
