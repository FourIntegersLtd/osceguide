"use client";

import { useCallback, useState } from "react";
import {
  Alert,
  AsyncBoundary,
  B2CSegmentedTabs,
  Badge,
  Button,
  Checkbox,
  LoadMore,
  Panel,
  PlatformPageHeader,
  Row,
  RowList,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { errorMessage, useCursorPages, useToast } from "@/foundation/hooks";
import {
  listSiteMessages,
  markMessageHandled,
  type SiteMessage,
} from "@/domains/platform/api";
import { formatDay } from "@/domains/platform/support";

/** A page at a time from the server. */
const MESSAGES_PAGE_LIMIT = 25;

type Kind = "all" | "contact" | "product_feedback";

const KIND_TABS: B2CSegmentedTabItem<Kind>[] = [
  { id: "all", label: "All" },
  { id: "contact", label: "Contact" },
  { id: "product_feedback", label: "Product feedback" },
];

/**
 * The contact and feedback inbox.
 *
 * A person writes to us from the public contact form or the "Help us improve"
 * box inside the product, and `POST /site/messages` files it. The two kinds
 * are separated because they have different endings — a contact note wants a
 * reply, a product suggestion wants triage — and "Handled" is deliberately the
 * only action: the platform sends no outbound mail through this slice.
 */
export function MessagesInbox() {
  const [kind, setKind] = useState<Kind>("all");
  // Unticked asks the server only for open messages; ticked asks for both.
  const [showHandled, setShowHandled] = useState(false);
  const pages = useCursorPages(
    (cursor, signal) =>
      listSiteMessages(
        {
          kind: kind === "all" ? "" : kind,
          handled: showHandled ? null : false,
          cursor,
          limit: MESSAGES_PAGE_LIMIT,
        },
        signal,
      ),
    [kind, showHandled],
  );
  const state = pages.state;

  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="Messages"
        description="What people have written to the platform."
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <B2CSegmentedTabs
          items={KIND_TABS}
          value={kind}
          onChange={setKind}
          compact
          aria-label="Message kind"
        />
        <Checkbox
          label="Show handled"
          checked={showHandled}
          onChange={(event) => setShowHandled(event.target.checked)}
        />
      </div>

      <AsyncBoundary
        state={state}
        isEmpty={(items) => items.length === 0}
        empty={{
          title: "Nothing waiting",
          description: showHandled
            ? "No messages of that kind have arrived."
            : "Every message of that kind has been handled.",
        }}
      >
        {(items) => (
          <Panel padding="none">
            <RowList flush>
              {items.map((message) => (
                <MessageRow
                  key={message.id}
                  message={message}
                  onReload={state.reload}
                />
              ))}
            </RowList>
            <LoadMore
              hasMore={pages.hasMore}
              busy={pages.loadingMore}
              onLoad={pages.loadMore}
              error={pages.moreError}
            />
          </Panel>
        )}
      </AsyncBoundary>
    </div>
  );
}

function MessageRow({
  message,
  onReload,
}: {
  message: SiteMessage;
  onReload: () => void;
}) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handle = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await markMessageHandled(message.id);
      toast.success("Marked handled");
      onReload();
    } catch (cause) {
      // Stay in the queue. A row that says "handled" when the write failed is
      // how a message gets lost.
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [message.id, onReload, toast]);

  const kindLabel =
    message.kind === "product_feedback" ? "Product feedback" : "Contact";
  const sender = message.name ?? message.email ?? "Anonymous";

  return (
    <Row className="items-start">
      <div className="min-w-0 flex-1">
        <p className="text-osce-data font-semibold text-ink">
          {message.subject ??
            (message.kind === "contact" ? "Contact" : "Suggestion")}
        </p>
        <p className="mt-0.5 text-osce-meta text-ink-subtle">
          {kindLabel} · {sender} · {formatDay(message.created_at)}
          {message.source ? ` · ${message.source}` : ""}
        </p>
        <p className="mt-2 whitespace-pre-wrap text-osce-body text-ink-muted">
          {message.body}
        </p>
        {error ? (
          <Alert tone="danger" className="mt-3">
            {error}
          </Alert>
        ) : null}
      </div>
      {message.handled_at ? (
        <Badge tone="neutral">Handled {formatDay(message.handled_at)}</Badge>
      ) : (
        <Button
          size="sm"
          variant="secondary"
          onClick={() => handle()}
          disabled={busy}
        >
          {busy ? "Saving…" : "Mark handled"}
        </Button>
      )}
    </Row>
  );
}
