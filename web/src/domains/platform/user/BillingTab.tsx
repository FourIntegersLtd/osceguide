"use client";

import { useCallback, useState } from "react";
import { Alert, Button, DetailLayout, Input, Panel, Select } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { listPlatformPlans, recordManualPayment } from "@/domains/platform/support/api";
import { BillingEvents } from "@/domains/platform/billing/BillingEvents";
import { Payments } from "@/domains/platform/billing/Payments";

/**
 * "I paid and nothing happened" is one of three rows, and this tab shows all
 * three: a payment that exists and granted access; a delivery that was
 * recorded and refused — an address with no account at the time — which
 * Replay applies once the cause is fixed; or no delivery at all, for which
 * the manual record exists.
 */
export function BillingTab({ userId }: { userId: string }) {
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  return (
    <DetailLayout
      main={
        <>
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
        </>
      }
      rail={<ManualPaymentPanel userId={userId} onRecorded={reload} />}
    />
  );
}

function ManualPaymentPanel({
  userId,
  onRecorded,
}: {
  userId: string;
  onRecorded: () => void;
}) {
  const toast = useToast();
  // A pick list of the real plans, on sale first: typing a code invited a
  // guess ("sca_1m") that matched no plan and was refused.
  const plans = useAsync((signal) => listPlatformPlans(signal), []);
  const choices = [...(plans.data?.items ?? [])].sort(
    (a, b) => Number(b.active) - Number(a.active) || a.code.localeCompare(b.code),
  );
  const [planCode, setPlanCode] = useState("");
  const [reference, setReference] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const pence = amount.trim() ? Math.round(Number(amount) * 100) : null;
      await recordManualPayment(userId, {
        planCode: planCode.trim(),
        reference: reference.trim() || null,
        amountPence: Number.isFinite(pence) ? pence : null,
        note: note.trim(),
      });
      toast.success(
        "Payment recorded",
        "Access given and a receipt created, just as a card payment would.",
      );
      setNote("");
      onRecorded();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel
      title="Record a payment"
      description="For money that did not come through Stripe, such as a bank transfer, a sponsor or a free place. It gives access and a receipt, just like paying online."
      padding="sm"
    >
      <form onSubmit={submit} className="flex flex-col gap-3">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        {plans.error ? (
          <Alert tone="danger">Could not load the plans: {errorMessage(plans.error)}</Alert>
        ) : null}
        <Select
          label="Plan"
          value={planCode}
          onChange={(event) => setPlanCode(event.target.value)}
          disabled={busy || plans.loading}
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
          label="Reference"
          value={reference}
          onChange={(event) => setReference(event.target.value)}
          disabled={busy}
          hint="A Stripe payment reference or a bank reference. Leave it blank and one is created for you."
        />
        <Input
          label="Amount paid"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          disabled={busy}
          hint="In pounds. Leave it blank to use the plan’s price."
          inputMode="decimal"
        />
        <Input
          label="Why"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          disabled={busy}
          required
          hint="Goes in the audit log."
        />
        <div className="flex justify-end">
          <Button
            type="submit"
            disabled={busy || !planCode.trim() || !note.trim()}
          >
            {busy ? "Recording…" : "Record payment"}
          </Button>
        </div>
      </form>
    </Panel>
  );
}
