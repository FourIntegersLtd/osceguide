"use client";

import { useCallback, useState } from "react";
import { Alert, Button, DetailLayout, Input, Panel } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import { recordManualPayment } from "@/domains/platform/support/api";
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
            title="Stripe deliveries"
            description="Every delivery naming this address. A refused one is the 'paid but no access' case: fix the cause, then replay."
            empty={{
              title: "No deliveries",
              description: "Stripe has sent nothing for this address.",
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
  const [planCode, setPlanCode] = useState("");
  const [reference, setReference] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(
    async (event: React.FormEvent) => {
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
          "Access granted and a receipt minted, as a card payment would.",
        );
        setNote("");
        onRecorded();
      } catch (cause) {
        setError(errorMessage(cause));
      } finally {
        setBusy(false);
      }
    },
    [userId, planCode, reference, amount, note, toast, onRecorded],
  );

  return (
    <Panel
      title="Record a payment"
      description="For money that did not come through Stripe — a bank transfer, a sponsor, a comped seat. Takes the same steps a checkout does."
      padding="sm"
    >
      <form onSubmit={submit} className="flex flex-col gap-3">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        <Input
          label="Plan code"
          value={planCode}
          onChange={(event) => setPlanCode(event.target.value)}
          disabled={busy}
          required
          hint="As listed on the pricing page, e.g. one_month."
        />
        <Input
          label="Reference"
          value={reference}
          onChange={(event) => setReference(event.target.value)}
          disabled={busy}
          hint="A Stripe intent id or a bank reference. Left empty, one is minted."
        />
        <Input
          label="Amount paid"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          disabled={busy}
          hint="In pounds. Left empty, the plan's price."
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
