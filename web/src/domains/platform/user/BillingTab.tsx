"use client";

import { useCallback, useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, Card, Input } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import {
  listUserBillingEvents,
  listUserPayments,
  recordManualPayment,
  recordRefund,
  replayBillingEvent,
  type PlatformPayment,
  type StripeEvent,
} from "@/domains/platform/support/api";
import { Row, RowList, Section } from "@/domains/platform/chrome";
import { InlineAction } from "@/domains/platform/user/InlineAction";
import { formatMoment, formatMoney } from "@/domains/platform/support";

/**
 * "I paid and nothing happened" is one of three rows, and this tab shows all
 * three: a payment that exists and granted access; a delivery that was
 * recorded and refused — an address with no account at the time — which
 * Replay applies once the cause is fixed; or no delivery at all, for which
 * the manual record exists.
 */
export function BillingTab({ userId }: { userId: string }) {
  const payments = useAsync((signal) => listUserPayments(userId, signal), [userId]);
  const events = useAsync((signal) => listUserBillingEvents(userId, signal), [userId]);
  const reload = useCallback(() => {
    payments.reload();
    events.reload();
  }, [payments, events]);

  return (
    <div className="flex flex-col gap-8">
      <Section title="Payments" description="What was paid, and what each payment bought.">
        <AsyncBoundary
          state={payments}
          isEmpty={(page) => page.items.length === 0}
          empty={{ title: "No payments", description: "Nothing has been recorded against this account." }}
        >
          {(page) => (
            <RowList>
              {page.items.map((payment) => (
                <PaymentRow key={payment.id} payment={payment} onChanged={reload} />
              ))}
            </RowList>
          )}
        </AsyncBoundary>
      </Section>

      <Section
        title="Webhook deliveries"
        description="Every Stripe delivery naming this address. A refused one with a reason is the 'paid but no access' case: fix the cause, then replay."
      >
        <AsyncBoundary
          state={events}
          isEmpty={(page) => page.items.length === 0}
          empty={{ title: "No deliveries", description: "Stripe has sent nothing for this address." }}
        >
          {(page) => (
            <RowList>
              {page.items.map((event) => (
                <EventRow key={event.event_id} event={event} onChanged={reload} />
              ))}
            </RowList>
          )}
        </AsyncBoundary>
      </Section>

      <ManualPaymentPanel userId={userId} onRecorded={reload} />
    </div>
  );
}

function PaymentRow({ payment, onChanged }: { payment: PlatformPayment; onChanged: () => void }) {
  const toast = useToast();
  return (
    <Row className="flex-col items-stretch sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-ink">
          {formatMoney(payment.amount_total_pence, payment.currency)} · {payment.plan_code ?? "no plan"}
        </p>
        <p className="truncate text-xs text-ink-subtle">
          {formatMoment(payment.paid_at)} · {payment.receipt_id ?? "no receipt"} · {payment.stripe_payment_intent_id}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={payment.entitlement_id ? "success" : "neutral"}>
          {payment.entitlement_id ? "Granted" : "No grant"}
        </Badge>
        <InlineAction
          label="Record refund"
          tone="danger"
          description="Record-only: refund the money in the Stripe dashboard. This withdraws the access it bought and keeps the payment."
          onConfirm={async (reason) => {
            await recordRefund(payment.id, reason);
            toast.success("Refund recorded", "The access this payment bought has been revoked.");
            onChanged();
          }}
        />
      </div>
    </Row>
  );
}

export function EventRow({ event, onChanged }: { event: StripeEvent; onChanged: () => void }) {
  const toast = useToast();
  const refused = !event.processed_at && !!event.failure;
  return (
    <Row className="flex-col items-stretch sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-ink">
          {event.event_type} · {event.customer_email ?? "no address"}
        </p>
        <p className="truncate text-xs text-ink-subtle">
          {formatMoment(event.received_at)} · {event.event_id}
          {event.price_id ? ` · ${event.price_id}` : ""}
          {event.failure ? ` · ${event.failure}` : ""}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={event.processed_at ? "success" : refused ? "danger" : "neutral"}>
          {event.processed_at ? "Applied" : refused ? "Refused" : "Pending"}
        </Badge>
        {refused ? (
          <InlineAction
            label="Replay"
            requireReason={false}
            reasonLabel="Note"
            description="Applies the delivery again. Works once its cause is fixed — the account exists, the plan exists."
            onConfirm={async () => {
              const result = await replayBillingEvent(event.event_id);
              toast.success(`Replay: ${result.status.replace(/_/g, " ")}`);
              onChanged();
            }}
          />
        ) : null}
      </div>
    </Row>
  );
}

function ManualPaymentPanel({ userId, onRecorded }: { userId: string; onRecorded: () => void }) {
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
        toast.success("Payment recorded", "Access granted and a receipt minted, as a card payment would.");
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
    <Section
      title="Record a payment"
      description="For money that did not come through Stripe — a bank transfer, a sponsor, a comped seat. Takes the same steps a checkout does."
    >
      <Card padding="md">
        <form onSubmit={submit} className="flex max-w-lg flex-col gap-3">
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <Input label="Plan code" value={planCode} onChange={(event) => setPlanCode(event.target.value)} disabled={busy} required hint="As listed on the pricing page, e.g. one_month." />
          <Input label="Reference" value={reference} onChange={(event) => setReference(event.target.value)} disabled={busy} hint="A Stripe intent id or a bank reference. Left empty, one is minted." />
          <Input label="Amount paid" value={amount} onChange={(event) => setAmount(event.target.value)} disabled={busy} hint="In pounds. Left empty, the plan's price." inputMode="decimal" />
          <Input label="Why" value={note} onChange={(event) => setNote(event.target.value)} disabled={busy} required hint="Goes in the audit log." />
          <div className="flex justify-end">
            <Button type="submit" disabled={busy || !planCode.trim() || !note.trim()}>
              {busy ? "Recording…" : "Record payment"}
            </Button>
          </div>
        </form>
      </Card>
    </Section>
  );
}
