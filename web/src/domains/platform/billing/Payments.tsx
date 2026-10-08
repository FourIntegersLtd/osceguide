"use client";

import {
  AsyncBoundary,
  Badge,
  LoadMore,
  Panel,
  Row,
  RowList,
} from "@/foundation/ui";
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
    <Panel
      title="Payments"
      description="What was paid, and what each payment bought."
      padding="none"
    >
      <AsyncBoundary
        state={pages.state}
        isEmpty={(items) => items.length === 0}
        empty={{
          title: "No payments",
          description: "Nothing has been recorded against this account.",
          bare: true,
        }}
      >
        {(items) => (
          <>
            <RowList flush>
              {items.map((payment) => (
                <PaymentRow
                  key={payment.id}
                  payment={payment}
                  onChanged={pages.state.reload}
                />
              ))}
            </RowList>
            <LoadMore
              hasMore={pages.hasMore}
              busy={pages.loadingMore}
              onLoad={pages.loadMore}
              error={pages.moreError}
            />
          </>
        )}
      </AsyncBoundary>
    </Panel>
  );
}

function PaymentRow({
  payment,
  onChanged,
}: {
  payment: PlatformPayment;
  onChanged: () => void;
}) {
  const toast = useToast();
  const granted = payment.entitlement_id !== null && !payment.access_revoked;
  return (
    <Row>
      <div className="min-w-0 flex-1">
        <p className="truncate text-osce-data font-medium text-ink">
          {formatMoney(payment.amount_total_pence, payment.currency)} ·{" "}
          {payment.plan_code ?? "no plan"}
        </p>
        <p className="truncate text-osce-meta text-ink-subtle">
          {formatMoment(payment.paid_at)} · {payment.receipt_id ?? "no receipt"}{" "}
          · {payment.stripe_payment_intent_id}
        </p>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <Badge tone={granted ? "success" : "neutral"}>
          {granted ? "Granted" : payment.entitlement_id ? "Access withdrawn" : "No grant"}
        </Badge>
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
    </Row>
  );
}
