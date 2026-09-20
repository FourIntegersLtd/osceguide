"use client";

import { useCallback, useMemo } from "react";
import Table, {
  type FetchPageParams,
  type FetchPageResult,
} from "@/foundation/table/Table";
import { Badge } from "@/foundation/ui";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import { useToast } from "@/foundation/hooks";
import {
  listUserPayments,
  recordRefund,
  type PlatformPayment,
} from "@/domains/platform/support/api";
import { formatMoment, formatMoney } from "@/domains/platform/support";
import { InlineAction } from "@/domains/platform/user/InlineAction";

export function UserBillingPaymentsTable({
  userId,
  onChanged,
  empty,
}: {
  userId: string;
  onChanged: () => void;
  empty: { title: string; description?: string };
}) {
  const toast = useToast();

  const fetchPage = useCallback(
    async (params: FetchPageParams): Promise<FetchPageResult<PlatformPayment>> => {
      const page = await listUserPayments(userId, {
        limit: params.perPage,
        cursor: params.cursor ?? undefined,
      });
      return {
        items: page.items,
        nextCursor: page.next_cursor ?? null,
        hasMore: Boolean(page.next_cursor),
      };
    },
    [userId],
  );

  const columns = useMemo(
    () => [
      {
        header: "Payment",
        key: "id" as keyof PlatformPayment,
        priority: "primary" as const,
        render: (payment: PlatformPayment) => (
          <div className="min-w-0">
            <p className={cn(b2cTableCellText, "font-medium text-osce-ink-900")}>
              {formatMoney(payment.amount_total_pence, payment.currency)} ·{" "}
              {payment.plan_code ?? "no plan"}
            </p>
            <p className={cn("truncate text-xs text-b2c-text-muted", b2cTableCellText)}>
              {formatMoment(payment.paid_at)} · {payment.receipt_id ?? "no receipt"} ·{" "}
              {payment.stripe_payment_intent_id}
            </p>
          </div>
        ),
      },
      {
        header: "Grant",
        key: "entitlement_id" as keyof PlatformPayment,
        render: (payment: PlatformPayment) => (
          <Badge tone={payment.entitlement_id ? "success" : "neutral"}>
            {payment.entitlement_id ? "Granted" : "No grant"}
          </Badge>
        ),
      },
      {
        header: "Actions",
        key: "stripe_payment_intent_id" as keyof PlatformPayment,
        priority: "detail" as const,
        render: (payment: PlatformPayment) => (
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
        ),
      },
    ],
    [onChanged, toast],
  );

  return (
    <Table<PlatformPayment>
      fetchPage={fetchPage}
      columns={columns}
      idField="id"
      nameField="plan_code"
      showSearch={false}
      defaultItemsPerPage={25}
      empty={empty}
    />
  );
}
