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
  type PlatformPayment,
} from "@/domains/platform/support/api";
import { formatMoment, formatMoney } from "@/domains/platform/support";
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
        <Badge tone={payment.entitlement_id ? "success" : "neutral"}>
          {payment.entitlement_id ? "Granted" : "No grant"}
        </Badge>
        <InlineAction
          label="Record refund"
          tone="danger"
          description="Record-only: refund the money in the Stripe dashboard. This withdraws the access it bought and keeps the payment."
          onConfirm={async (reason) => {
            await recordRefund(payment.id, reason);
            toast.success(
              "Refund recorded",
              "The access this payment bought has been revoked.",
            );
            onChanged();
          }}
        />
      </div>
    </Row>
  );
}
