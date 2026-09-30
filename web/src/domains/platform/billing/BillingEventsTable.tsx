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
  listBillingEvents,
  listUserBillingEvents,
  replayBillingEvent,
  type StripeEvent,
} from "@/domains/platform/support/api";
import { formatMoment } from "@/domains/platform/support";
import { InlineAction } from "@/domains/platform/user/InlineAction";

function useBillingEventColumns(onChanged: () => void) {
  const toast = useToast();
  return useMemo(
    () => [
      {
        header: "Delivery",
        key: "event_type" as keyof StripeEvent,
        priority: "primary" as const,
        render: (event: StripeEvent) => (
          <div className="min-w-0">
            <p className={cn(b2cTableCellText, "truncate font-medium text-osce-ink-900")}>
              {event.event_type} · {event.customer_email ?? "no address"}
            </p>
            <p className={cn("truncate text-osce-meta text-b2c-text-muted", b2cTableCellText)}>
              {formatMoment(event.received_at)} · {event.event_id}
              {event.price_id ? ` · ${event.price_id}` : ""}
              {event.failure ? ` · ${event.failure}` : ""}
            </p>
          </div>
        ),
      },
      {
        header: "Status",
        key: "processed_at" as keyof StripeEvent,
        render: (event: StripeEvent) => {
          const refused = !event.processed_at && !!event.failure;
          return (
            <Badge tone={event.processed_at ? "success" : refused ? "danger" : "neutral"}>
              {event.processed_at ? "Applied" : refused ? "Refused" : "Pending"}
            </Badge>
          );
        },
      },
      {
        header: "Actions",
        key: "event_id" as keyof StripeEvent,
        priority: "detail" as const,
        render: (event: StripeEvent) => {
          const refused = !event.processed_at && !!event.failure;
          if (!refused) return null;
          return (
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
          );
        },
      },
    ],
    [onChanged, toast],
  );
}

/** Platform-wide webhook ledger (billing queue). */
export function PlatformBillingEventsTable({
  failedOnly,
  onChanged,
  empty,
}: {
  failedOnly: boolean;
  onChanged?: () => void;
  empty: { title: string; description?: string };
}) {
  const columns = useBillingEventColumns(onChanged ?? (() => undefined));

  const fetchPage = useCallback(
    async (params: FetchPageParams): Promise<FetchPageResult<StripeEvent>> => {
      const page = await listBillingEvents({
        failedOnly,
        limit: params.perPage,
        cursor: params.cursor ?? undefined,
      });
      return {
        items: page.items,
        nextCursor: page.next_cursor ?? null,
        hasMore: Boolean(page.next_cursor),
      };
    },
    [failedOnly],
  );

  return (
    <Table<StripeEvent>
      fetchPage={fetchPage}
      columns={columns}
      idField="event_id"
      nameField="event_type"
      showSearch={false}
      defaultItemsPerPage={25}
      empty={empty}
    />
  );
}

/** One account's webhook deliveries. */
export function UserBillingEventsTable({
  userId,
  onChanged,
  empty,
}: {
  userId: string;
  onChanged: () => void;
  empty: { title: string; description?: string };
}) {
  const columns = useBillingEventColumns(onChanged);

  const fetchPage = useCallback(
    async (params: FetchPageParams): Promise<FetchPageResult<StripeEvent>> => {
      const page = await listUserBillingEvents(userId, {
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

  return (
    <Table<StripeEvent>
      fetchPage={fetchPage}
      columns={columns}
      idField="event_id"
      nameField="event_type"
      showSearch={false}
      defaultItemsPerPage={25}
      empty={empty}
    />
  );
}
