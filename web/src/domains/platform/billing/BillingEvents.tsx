"use client";

import type { ReactNode } from "react";
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
  listBillingEvents,
  listUserBillingEvents,
  replayBillingEvent,
  type StripeEvent,
} from "@/domains/platform/support/api";
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
    <Panel
      title={title}
      description={description}
      actions={actions}
      padding="none"
    >
      <AsyncBoundary
        state={pages.state}
        isEmpty={(items) => items.length === 0}
        empty={{ ...empty, bare: true }}
      >
        {(items) => (
          <>
            <RowList flush>
              {items.map((event) => (
                <EventRow
                  key={event.event_id}
                  event={event}
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

function EventRow({
  event,
  onChanged,
}: {
  event: StripeEvent;
  onChanged: () => void;
}) {
  const toast = useToast();
  const refused = !event.processed_at && !!event.failure;
  return (
    <Row>
      <div className="min-w-0 flex-1">
        <p className="truncate text-osce-data font-medium text-ink">
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
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <Badge
          tone={event.processed_at ? "success" : refused ? "danger" : "neutral"}
        >
          {event.processed_at ? "Applied" : refused ? "Refused" : "Pending"}
        </Badge>
        {refused ? (
          <InlineAction
            label="Try again"
            requireReason={false}
            reasonLabel="Note"
            description="Tries this payment update again. It only works once the problem is fixed, for example once the account or the plan exists."
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
