"use client";

import { useCallback, useMemo, useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, Panel } from "@/foundation/ui";
import { errorMessage, useAsync, useToast, type AsyncState } from "@/foundation/hooks";
import {
  listPlatformPlans,
  listUserBillingAccess,
  listUserBillingEvents,
  recordRefund,
  refundInStripe,
  revokeEntitlement,
  type PlatformAccessGrant,
  type PlatformExamAccess,
  type PlatformPlan,
} from "@/domains/platform/support/api";
import { formatDay } from "@/domains/platform/support";
import { BillingEvents } from "@/domains/platform/billing/BillingEvents";
import { GiveAccessPanel } from "@/domains/platform/user/GiveAccessPanel";
import { InlineAction } from "@/domains/platform/user/InlineAction";
import {
  GRANT_STATE_LABEL,
  accessLine,
  grantPaymentLine,
  grantState,
  planName,
  sourceLabel,
} from "@/domains/platform/user/accessCopy";

/**
 * The one place access is seen and changed, in three blocks: the access they have (every grant,
 * with what it cost and the one action it allows), giving access by choosing a plan, and any
 * payment that did not reach them.
 *
 * Access is only ever given by choosing a plan, so a free place, a sponsor or a goodwill month is
 * a plan with the amount left blank.
 */
export function BillingTab({ userId, email }: { userId: string; email: string }) {
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => setReloadKey((current) => current + 1), []);
  // Fetched once here and shared, so the access block and the give-access form always agree.
  const access = useAsync((signal) => listUserBillingAccess(userId, signal), [userId, reloadKey]);
  const plans = useAsync((signal) => listPlatformPlans(signal), []);

  return (
    <div className="flex flex-col gap-6">
      <AccessSection access={access} plans={plans.data?.items ?? []} email={email} onChanged={reload} />
      <GiveAccessPanel
        userId={userId}
        email={email}
        plans={plans}
        accessRows={access.data?.items ?? []}
        onGiven={reload}
      />
      <PaymentProblems userId={userId} reloadKey={reloadKey} />
    </div>
  );
}

/** Per exam: what they can use today, then the grants behind it. Finished grants fold away. */
function AccessSection({
  access,
  plans,
  email,
  onChanged,
}: {
  access: AsyncState<{ items: PlatformExamAccess[] }>;
  plans: PlatformPlan[];
  email: string;
  onChanged: () => void;
}) {
  const durations = useMemo(() => new Map(plans.map((plan) => [plan.code, plan.duration_days])), [plans]);
  const plansByCode = useMemo(() => new Map(plans.map((plan) => [plan.code, plan])), [plans]);
  const now = new Date();

  return (
    <Panel
      title="Access"
      description="What they can use today for each exam, and every grant behind it. They can use an exam while any one of its grants is live."
      padding="sm"
    >
      <AsyncBoundary state={access}>
        {(page) =>
          page.items.length === 0 ? (
            <p className="text-osce-data text-ink-muted">No access to any exam.</p>
          ) : (
            <div className="flex flex-col gap-5">
              {page.items.map((row) => {
                const states = row.grants.map((grant) => ({ grant, state: grantState(grant, now) }));
                const current = states.filter(({ state }) => state === "live" || state === "starts_later");
                const past = states.filter(({ state }) => state === "ended" || state === "revoked");
                return (
                  <section key={row.exam_code} className="flex flex-col gap-2">
                    <p className="font-medium text-ink">{accessLine(row, durations)}</p>
                    {current.length > 0 ? (
                      <ul className="flex flex-col gap-3">
                        {current.map(({ grant, state }) => (
                          <GrantRow
                            key={grant.entitlement_id}
                            grant={grant}
                            state={state}
                            plan={grant.plan_code ? plansByCode.get(grant.plan_code) : undefined}
                            email={email}
                            onChanged={onChanged}
                          />
                        ))}
                      </ul>
                    ) : null}
                    {past.length > 0 ? (
                      <details>
                        <summary className="cursor-pointer text-osce-meta text-ink-muted">
                          Past access ({past.length})
                        </summary>
                        <ul className="mt-2 flex flex-col gap-3">
                          {past.map(({ grant, state }) => (
                            <GrantRow
                              key={grant.entitlement_id}
                              grant={grant}
                              state={state}
                              plan={grant.plan_code ? plansByCode.get(grant.plan_code) : undefined}
                              email={email}
                              onChanged={onChanged}
                            />
                          ))}
                        </ul>
                      </details>
                    ) : null}
                  </section>
                );
              })}
            </div>
          )
        }
      </AsyncBoundary>
    </Panel>
  );
}

/** One grant: what it is, when it runs, what it cost, and (while it can still be undone) its one action. */
function GrantRow({
  grant,
  state,
  plan,
  email,
  onChanged,
}: {
  grant: PlatformAccessGrant;
  state: ReturnType<typeof grantState>;
  plan: PlatformPlan | undefined;
  email: string;
  onChanged: () => void;
}) {
  const paymentLine = grantPaymentLine(grant);
  const isCurrent = state === "live" || state === "starts_later";
  return (
    <li className="flex flex-wrap items-start justify-between gap-2">
      <div className="min-w-0">
        <p className="font-medium text-ink">{plan ? planName(plan) : (grant.plan_code ?? sourceLabel(grant.source))}</p>
        <p className="text-osce-meta text-ink-subtle">
          {sourceLabel(grant.source)} · {formatDay(grant.starts_at)} to{" "}
          {grant.ends_at ? formatDay(grant.ends_at) : "no end date"}
        </p>
        {paymentLine ? <p className="text-osce-meta text-ink-subtle">{paymentLine}</p> : null}
      </div>
      <div className="flex items-center gap-2">
        <Badge dot tone={state === "live" ? "success" : state === "starts_later" ? "warning" : "neutral"}>
          {GRANT_STATE_LABEL[state]}
        </Badge>
        {isCurrent ? <GrantAction grant={grant} email={email} onChanged={onChanged} /> : null}
      </div>
    </li>
  );
}

/**
 * Revoke for a grant that was not bought, Refund for one that was. Both name the person. A Stripe
 * payment is refunded in Stripe; any other (a manual or imported one) records a refund made
 * elsewhere, with no money moved.
 */
function GrantAction({
  grant,
  email,
  onChanged,
}: {
  grant: PlatformAccessGrant;
  email: string;
  onChanged: () => void;
}) {
  const toast = useToast();
  if (grant.source !== "purchase") {
    return (
      <InlineAction
        label="Revoke"
        tone="danger"
        description={`This removes the access ${email} has from this grant.`}
        onConfirm={async (reason) => {
          await revokeEntitlement(grant.entitlement_id, reason);
          toast.success("Access revoked");
          onChanged();
        }}
      />
    );
  }
  const { payment_id: paymentId, payment_reference: paymentReference } = grant;
  if (paymentId === null || paymentReference === null) {
    return <span className="text-osce-meta text-ink-subtle">No payment is linked to this grant</span>;
  }
  const inStripe = paymentReference.startsWith("pi_");
  return (
    <InlineAction
      label="Refund"
      tone="danger"
      description={
        inStripe
          ? `This refunds the full amount to ${email} in Stripe, then removes the access it bought. If Stripe refuses, nothing changes.`
          : `This records a refund made outside this screen for ${email} and removes the access it bought. No money moves.`
      }
      onConfirm={async (reason) => {
        await (inStripe ? refundInStripe(paymentId, reason) : recordRefund(paymentId, reason));
        toast.success("Refunded", "The access this payment bought has been removed.");
        onChanged();
      }}
    />
  );
}

/**
 * Stripe updates matter when one failed: they paid but did not get access. With none failed this
 * is a single quiet line, and the full list is one click away.
 */
function PaymentProblems({ userId, reloadKey }: { userId: string; reloadKey: number }) {
  const events = useAsync(
    (signal) => listUserBillingEvents(userId, { limit: 25 }, signal),
    [userId, reloadKey],
  );
  const [showAll, setShowAll] = useState(false);
  const hasProblem = (events.data?.items ?? []).some((event) => Boolean(event.failure) || !event.processed_at);

  if (events.error) {
    return <Alert tone="danger">Could not load the Stripe updates: {errorMessage(events.error)}</Alert>;
  }
  if (events.loading) return null;
  if (!hasProblem && !showAll) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-osce-data text-ink-muted">No payment problems from Stripe.</p>
        <Button type="button" size="sm" variant="secondary" onClick={() => setShowAll(true)}>
          Show all Stripe updates
        </Button>
      </div>
    );
  }
  return (
    <BillingEvents
      key={reloadKey}
      userId={userId}
      title="Payment updates from Stripe"
      description="Every payment update from Stripe for this email address. A failed one means they paid but did not get access: fix the problem, then try it again."
      empty={{
        title: "No payment updates",
        description: "No payments from Stripe for this email address.",
      }}
    />
  );
}
