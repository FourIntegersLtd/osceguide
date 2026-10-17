"use client";

import { AsyncBoundary, Badge } from "@/foundation/ui";
import Table, { type Column } from "@/foundation/table/Table";
import { useCursorPages, useToast } from "@/foundation/hooks";
import {
  listUserPayments,
  recordRefund,
  refundInStripe,
  type PlatformPayment,
} from "@/domains/platform/support/api";
import { formatMoney } from "@/foundation/format";
import { formatMoment } from "@/domains/platform/support";
import { InlineAction } from "@/domains/platform/user/InlineAction";

const PAYMENTS_PAGE_LIMIT = 25;

/** One account's payments, and what each bought. */
export function Payments({
  userId,
  reloadKey,
}: {
  userId: string;
  reloadKey: number;
}) {
  const pages = useCursorPages(
    (cursor, signal) =>
      listUserPayments(
        userId,
        { limit: PAYMENTS_PAGE_LIMIT, cursor: cursor ?? undefined },
        signal,
      ),
    [userId, reloadKey],
  );

  return (
    <AsyncBoundary state={pages.state}>
      {(items) => (
        <Table<PlatformPayment>
          rows={items}
          more={pages}
          themeType="b2b"
          idField="id"
          title="Payments"
          description="What was paid, and what each payment bought."
          empty={{
            title: "No payments",
            description: "Nothing has been recorded against this account.",
          }}
          columns={paymentColumns(pages.state.reload)}
        />
      )}
    </AsyncBoundary>
  );
}

const isGranted = (payment: PlatformPayment) =>
  payment.entitlement_id !== null && !payment.access_revoked;

function paymentColumns(onChanged: () => void): Column<PlatformPayment>[] {
  return [
    {
      header: "Payment",
      key: "id",
      priority: "primary",
      render: (payment) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-ink">
            {formatMoney(payment.amount_total_pence, payment.currency)} ·{" "}
            {payment.plan_code ?? "no plan"}
          </p>
          <p className="truncate text-osce-meta text-ink-subtle">
            {formatMoment(payment.paid_at)} · {payment.receipt_id ?? "no receipt"} ·{" "}
            {payment.stripe_payment_intent_id}
          </p>
        </div>
      ),
    },
    {
      header: "Access",
      key: "entitlement_id",
      render: (payment) => (
        <Badge tone={isGranted(payment) ? "success" : "neutral"} dot>
          {isGranted(payment)
            ? "Granted"
            : payment.entitlement_id
              ? "Access withdrawn"
              : "No grant"}
        </Badge>
      ),
    },
    {
      header: "",
      key: "paid_at",
      render: (payment) => <RefundActions payment={payment} onChanged={onChanged} />,
    },
  ];
}

function RefundActions({
  payment,
  onChanged,
}: {
  payment: PlatformPayment;
  onChanged: () => void;
}) {
  const toast = useToast();
  const granted = isGranted(payment);
  return (
    <div className="flex flex-wrap items-center gap-2">
    {/* Nothing to revoke once the grant is gone, so a second "refund" would only look like it did something. */}
    {granted && payment.stripe_payment_intent_id.startsWith("pi_") ? (
      <InlineAction
        label="Refund"
        tone="danger"
        description="Refunds the full amount to the customer's card in Stripe, then removes the access this payment bought. If Stripe refuses, nothing changes."
        onConfirm={async (reason) => {
          await refundInStripe(payment.id, reason);
          toast.success(
            "Refunded in Stripe",
            "The access this payment bought has been revoked.",
          );
          onChanged();
        }}
      />
    ) : null}
    {granted ? (
      <InlineAction
        label="Record refund"
        tone="danger"
        description="This does not move any money; use it for a refund made outside this screen. It removes the access this payment bought and keeps the payment on record."
        onConfirm={async (reason) => {
          await recordRefund(payment.id, reason);
          toast.success(
            "Refund recorded",
            "The access this payment bought has been revoked.",
          );
          onChanged();
        }}
      />
    ) : null}
    </div>
  );
}
