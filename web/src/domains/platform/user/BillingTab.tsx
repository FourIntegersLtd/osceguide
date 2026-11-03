"use client";

import { useCallback, useRef, useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, Checkbox, Input, Panel, Select } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import {
  listPlatformPlans,
  listUserBillingAccess,
  recordManualPayment,
  recordRefund,
  refundInStripe,
  revokeEntitlement,
  type PlatformAccessGrant,
} from "@/domains/platform/support/api";
import { amountPaidLabel, penceFrom } from "@/domains/platform/support/money";
import { formatDay } from "@/domains/platform/support";
import { BillingEvents } from "@/domains/platform/billing/BillingEvents";
import { Payments } from "@/domains/platform/billing/Payments";
import { InlineAction } from "@/domains/platform/user/InlineAction";
import {
  GRANT_STATE_LABEL,
  accessLine,
  grantState,
  planName,
  sourceLabel,
  startChoiceLabel,
} from "@/domains/platform/user/accessCopy";

/**
 * The one place access is seen and changed. Top to bottom: what they can use now, the grants
 * behind it, giving access by choosing a plan, then the payments and Stripe updates.
 *
 * Access is only ever given by choosing a plan, so a free place, a sponsor or a goodwill month is
 * a plan with the amount left blank.
 */
export function BillingTab({ userId, email }: { userId: string; email: string }) {
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => setReloadKey((current) => current + 1), []);

  return (
    <div className="flex flex-col gap-6">
      <AccessNow userId={userId} reloadKey={reloadKey} />
      <Grants userId={userId} email={email} reloadKey={reloadKey} onChanged={reload} />
      <GiveAccessPanel userId={userId} email={email} onGiven={reload} />
      <Payments userId={userId} reloadKey={reloadKey} />
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
    </div>
  );
}

/** One line per exam saying what they can use today. */
function AccessNow({ userId, reloadKey }: { userId: string; reloadKey: number }) {
  const access = useAsync((signal) => listUserBillingAccess(userId, signal), [userId, reloadKey]);
  const plans = useAsync((signal) => listPlatformPlans(signal), []);
  const durations = new Map((plans.data?.items ?? []).map((plan) => [plan.code, plan.duration_days]));

  return (
    <Panel title="Access now" description="What they can use today, for each exam." padding="sm">
      <AsyncBoundary state={access}>
        {(page) =>
          page.items.length === 0 ? (
            <p className="text-osce-data text-ink-muted">No access to any exam.</p>
          ) : (
            <ul className="flex flex-col gap-1">
              {page.items.map((row) => (
                <li key={row.exam_code} className="text-osce-data text-ink">
                  {accessLine(row, durations)}
                </li>
              ))}
            </ul>
          )
        }
      </AsyncBoundary>
    </Panel>
  );
}

/** Every grant behind their access, with Revoke for free ones and Refund for purchases. */
function Grants({
  userId,
  email,
  reloadKey,
  onChanged,
}: {
  userId: string;
  email: string;
  reloadKey: number;
  onChanged: () => void;
}) {
  const access = useAsync((signal) => listUserBillingAccess(userId, signal), [userId, reloadKey]);
  const now = new Date();

  return (
    <Panel
      title="Grants"
      description="Each grant behind their access. They can use an exam while any one of its grants is live."
      padding="sm"
    >
      <AsyncBoundary state={access}>
        {(page) => {
          const rows = page.items.flatMap((row) =>
            row.grants.map((grant) => ({ examCode: row.exam_code, grant })),
          );
          if (rows.length === 0) return <p className="text-osce-data text-ink-muted">No grants.</p>;
          return (
            <ul className="flex flex-col gap-3">
              {rows.map(({ examCode, grant }) => {
                const state = grantState(grant, now);
                return (
                  <li key={grant.entitlement_id} className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-medium text-ink">
                        {examCode.toUpperCase()} · {grant.plan_code ?? sourceLabel(grant.source)}
                      </p>
                      <p className="text-osce-meta text-ink-subtle">
                        {sourceLabel(grant.source)} · {formatDay(grant.starts_at)} to{" "}
                        {grant.ends_at ? formatDay(grant.ends_at) : "no end date"}
                      </p>
                    </div>
                    <Badge dot tone={state === "live" ? "success" : state === "starts_later" ? "warning" : "neutral"}>
                      {GRANT_STATE_LABEL[state]}
                    </Badge>
                    {state === "ended" || state === "revoked" ? null : (
                      <GrantAction grant={grant} email={email} onChanged={onChanged} />
                    )}
                  </li>
                );
              })}
            </ul>
          );
        }}
      </AsyncBoundary>
    </Panel>
  );
}

/** Revoke for a grant that was not bought, Refund for one that was. Both name the person. */
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
    return <span className="text-osce-meta text-ink-subtle">Refund this from Payments</span>;
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

/** Gives access by choosing a plan. A blank amount is a free place. */
function GiveAccessPanel({
  userId,
  email,
  onGiven,
}: {
  userId: string;
  email: string;
  onGiven: () => void;
}) {
  const toast = useToast();
  // A pick list of the real plans, on sale first: typing a code invited a guess that matched no plan.
  const plans = useAsync((signal) => listPlatformPlans(signal), []);
  const choices = [...(plans.data?.items ?? [])].sort(
    (first, second) => Number(second.active) - Number(first.active) || first.code.localeCompare(second.code),
  );
  const [planCode, setPlanCode] = useState("");
  const [amount, setAmount] = useState("");
  const [start, setStart] = useState<"now" | "after_current">("after_current");
  const [sendReceipt, setSendReceipt] = useState(false);
  const [note, setNote] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Made once when the confirm step opens and sent with every try, so a double submit grants once.
  const [reference, setReference] = useState("");
  const inFlight = useRef(false);

  const chosenPlan = choices.find((plan) => plan.code === planCode);
  const pence = penceFrom(amount);
  const amountInvalid = amount.trim() !== "" && pence === null;

  const save = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      await recordManualPayment(userId, {
        planCode,
        reference,
        amountPence: pence,
        sendReceipt,
        start,
        note: note.trim(),
      });
      toast.success("Access given", sendReceipt ? "A receipt was emailed." : "No receipt was emailed.");
      setNote("");
      setConfirming(false);
      onGiven();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  const review = (event: React.FormEvent) => {
    event.preventDefault();
    if (amountInvalid) {
      setError("Enter the amount as a number of pounds, such as 12 or 12.50.");
      return;
    }
    setError(null);
    setReference(`manual:${crypto.randomUUID()}`);
    setConfirming(true);
  };

  return (
    <Panel
      title="Give access"
      description="Choose a plan. Leave the amount blank for a free place, such as a bank transfer, a sponsor or a goodwill month."
      padding="sm"
    >
      <form onSubmit={review} className="flex flex-col gap-3">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        {plans.error ? (
          <Alert tone="danger">Could not load the plans: {errorMessage(plans.error)}</Alert>
        ) : null}
        <Select
          label="Plan"
          value={planCode}
          onChange={(event) => setPlanCode(event.target.value)}
          disabled={busy || confirming || plans.loading}
          required
        >
          <option value="">{plans.loading ? "Loading plans…" : "Choose a plan"}</option>
          {choices.map((plan) => (
            <option key={plan.code} value={plan.code}>
              {`${plan.exam_code.toUpperCase()} · £${(plan.amount_pence / 100).toFixed(2)} for ${plan.duration_days} days (${plan.code})${plan.active ? "" : " · retired"}`}
            </option>
          ))}
        </Select>
        <Input
          label="Amount paid"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          disabled={busy || confirming}
          hint="In pounds. Leave it blank for a free place."
          inputMode="decimal"
        />
        <fieldset className="flex flex-col gap-2" disabled={busy || confirming}>
          <legend className="text-osce-meta text-ink-muted">When it starts</legend>
          <label className="flex items-center gap-2 text-osce-data text-ink">
            <input
              type="radio"
              name="start"
              checked={start === "now"}
              onChange={() => setStart("now")}
              className="accent-accent"
            />
            Starts now
          </label>
          <label className="flex items-center gap-2 text-osce-data text-ink">
            <input
              type="radio"
              name="start"
              checked={start === "after_current"}
              onChange={() => setStart("after_current")}
              className="accent-accent"
            />
            Starts when the current plan ends
          </label>
        </fieldset>
        <Checkbox
          label="Email a receipt"
          checked={sendReceipt}
          onChange={(event) => setSendReceipt(event.target.checked)}
          disabled={busy || confirming}
        />
        <Input
          label="Why"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          disabled={busy || confirming}
          required
          hint="Goes in the audit log."
        />
        {confirming ? (
          <Alert tone="warning">
            <p>
              Give {email} the {chosenPlan ? planName(chosenPlan) : planCode} for {amountPaidLabel(pence)}. It{" "}
              {startChoiceLabel(start)}.
            </p>
            <div className="mt-2 flex gap-2">
              <Button type="button" size="sm" disabled={busy} onClick={save}>
                {busy ? "Saving…" : "Confirm and give access"}
              </Button>
              <Button type="button" size="sm" variant="secondary" disabled={busy} onClick={() => setConfirming(false)}>
                Cancel
              </Button>
            </div>
          </Alert>
        ) : (
          <div className="flex justify-end">
            <Button type="submit" disabled={!planCode.trim() || !note.trim()}>
              Give access
            </Button>
          </div>
        )}
      </form>
    </Panel>
  );
}
