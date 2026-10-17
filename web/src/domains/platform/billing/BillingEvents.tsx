"use client";

import type { ReactNode } from "react";
import { AsyncBoundary, Badge } from "@/foundation/ui";
import Table, { type Column } from "@/foundation/table/Table";
import { useCursorPages, useToast } from "@/foundation/hooks";
import {
  listBillingEvents,
  listUserBillingEvents,
  replayBillingEvent,
  type StripeEvent,
} from "@/domains/platform/support/api";
import { humanise } from "@/foundation/format";
import { formatMoment } from "@/domains/platform/support";
import { InlineAction } from "@/domains/platform/user/InlineAction";

const EVENTS_PAGE_LIMIT = 25;

/**
 * Stripe webhook deliveries: the platform-wide ledger, or one account's when
 * `userId` is given. A refused delivery can be replayed once its cause is fixed.
 */
export function BillingEvents({
  userId,
  failedOnly = false,
  title,
  description,
  actions,
  empty,
}: {
  userId?: string;
  failedOnly?: boolean;
  title: string;
  description?: string;
  actions?: ReactNode;
  empty: { title: string; description?: string };
}) {
  const pages = useCursorPages(
    (cursor, signal) => {
      const page = { limit: EVENTS_PAGE_LIMIT, cursor: cursor ?? undefined };
      return userId
        ? listUserBillingEvents(userId, page, signal)
        : listBillingEvents({ ...page, failedOnly }, signal);
    },
    [userId, failedOnly],
  );

  return (
    <div className="flex flex-col gap-4">
      {actions}
      <AsyncBoundary state={pages.state}>
        {(items) => (
          <Table<StripeEvent>
            rows={items}
            more={pages}
            themeType="b2b"
            idField="event_id"
            title={title}
            description={description}
            empty={empty}
            columns={eventColumns(pages.state.reload)}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}

function eventColumns(onChanged: () => void): Column<StripeEvent>[] {
  return [
    {
      header: "Delivery",
      key: "event_type",
      priority: "primary",
      render: (event) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-ink">
            {event.event_type} · {event.customer_email ?? "no address"}
          </p>
          <p className="truncate text-osce-meta text-ink-subtle">
            {formatMoment(event.received_at)} · {event.event_id}
            {event.price_id ? ` · ${event.price_id}` : ""}
          </p>
          {event.failure ? (
            <p className="mt-1 text-osce-meta text-ink-muted">{event.failure}</p>
          ) : null}
        </div>
      ),
    },
    {
      header: "Status",
      key: "processed_at",
      render: (event) => {
        const refused = !event.processed_at && !!event.failure;
        return (
          <Badge tone={event.processed_at ? "success" : refused ? "danger" : "neutral"} dot>
            {event.processed_at ? "Applied" : refused ? "Refused" : "Pending"}
          </Badge>
        );
      },
    },
    {
      header: "",
      key: "event_id",
      render: (event) => <ReplayAction event={event} onChanged={onChanged} />,
    },
  ];
}

function ReplayAction({
  event,
  onChanged,
}: {
  event: StripeEvent;
  onChanged: () => void;
}) {
  const toast = useToast();
  if (event.processed_at) return null;
  return (
    <InlineAction
      label="Try again"
      requireReason={false}
      reasonLabel="Note"
      description="Tries this payment update again. It only works once the problem is fixed, for example once the account or the plan exists."
      onConfirm={async () => {
        const result = await replayBillingEvent(event.event_id);
        toast.success(`Replay: ${humanise(result.status)}`);
        onChanged();
      }}
    />
  );
}
