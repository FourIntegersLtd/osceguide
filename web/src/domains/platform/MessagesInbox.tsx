"use client";

import { useState } from "react";
import {
  Alert,
  AsyncBoundary,
  B2CGroupedRow,
  B2CGroupedSection,
  B2CHero,
  B2CPageHeader,
  B2CSegmentedTabs,
  Badge,
  Button,
  Checkbox,
  LoadMore,
  Textarea,
  TextLink,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { errorMessage, useCursorPages, useToast } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import {
  listSiteMessages,
  markMessageHandled,
  replyToSiteMessage,
  type SiteMessage,
} from "@/domains/platform/api";
import { canReplyInApp, mailtoFor, waitingHeadline } from "@/domains/platform/queues";
import { formatDay, messageSourceLabel } from "@/domains/platform/support";

/** A page at a time from the server. */
const MESSAGES_PAGE_LIMIT = 25;

type Kind = "all" | "contact" | "product_feedback";

const KIND_TABS: B2CSegmentedTabItem<Kind>[] = [
  { id: "all", label: "All" },
  { id: "contact", label: "Contact" },
  { id: "product_feedback", label: "Product feedback" },
];

const kindLabel = (message: SiteMessage) =>
  message.kind === "product_feedback" ? "Product feedback" : "Contact";
const subjectOf = (message: SiteMessage) =>
  message.subject ?? (message.kind === "contact" ? "Contact" : "Suggestion");
const senderOf = (message: SiteMessage) => message.name ?? message.email ?? "Anonymous";

/** The opened message: what they wrote, and a reply to their inbox when they have one. */
function MessageCard({
  message,
  onChanged,
  onClose,
}: {
  message: SiteMessage;
  onChanged: () => void;
  onClose: () => void;
}) {
  const toast = useToast();
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noAccount, setNoAccount] = useState(false);
  const inApp = canReplyInApp(message) && !noAccount;
  const mailto = mailtoFor(message);

  const run = async (action: () => Promise<unknown>, done: string) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      toast.success(done);
      onChanged();
      onClose();
    } catch (cause) {
      // Stay in the queue: a row that says "handled" when the write failed is
      // how a message gets lost.
      if (hasCode(cause, "message_not_repliable")) setNoAccount(true);
      else setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <B2CGroupedSection
      eyebrow={subjectOf(message)}
      action={
        <span className="flex flex-wrap items-center gap-2">
          {inApp && !message.handled_at ? (
            <Button
              themeType="b2b" variant="commit"
              size="sm"
              isLoading={busy}
              disabled={!reply.trim()}
              onClick={() => run(() => replyToSiteMessage(message.id, reply.trim()), "Reply sent")}
            >
              Send reply
            </Button>
          ) : null}
          {message.handled_at ? null : (
            <Button
              variant="ghost"
              size="sm"
              disabled={busy}
              onClick={() => run(() => markMessageHandled(message.id), "Marked handled")}
            >
              Mark handled
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </span>
      }
    >
      <B2CGroupedRow title={`${kindLabel(message)} · ${senderOf(message)} · ${formatDay(message.created_at)}${
        message.source ? ` · ${messageSourceLabel(message.source)}` : ""
      }`} />
      <div className="flex flex-col gap-3 px-5 py-4">
        <p className="whitespace-pre-wrap text-osce-body text-ink">{message.body}</p>
        {error ? (
          <Alert tone="danger" className="mb-3">
            {error}
          </Alert>
        ) : null}
        {message.handled_at ? null : inApp ? (
          <Textarea
            label="Reply"
            value={reply}
            maxLength={5000}
            hint="Goes to the sender's inbox in the app."
            onChange={(event) => setReply(event.target.value)}
          />
        ) : (
          <Alert tone="info" className="mb-3">
            Sent without signing in, so there is no inbox to reply to.
            {mailto ? (
              <>
                {" "}
                Reply by email to <TextLink href={mailto}>{message.email}</TextLink>.
              </>
            ) : null}
          </Alert>
        )}
      </div>
    </B2CGroupedSection>
  );
}

/**
 * The contact and feedback inbox.
 *
 * A person writes to us from the public contact form or the "Help us improve"
 * box inside the product, and `POST /site/messages` files it. A signed-in
 * sender gets the reply in their inbox in the app; one who wrote signed out
 * has no inbox, so staff answer by email.
 */
export function MessagesInbox() {
  const [kind, setKind] = useState<Kind>("all");
  // Unticked asks the server only for open messages; ticked asks for both.
  const [showHandled, setShowHandled] = useState(false);
  const [opened, setOpened] = useState<SiteMessage | null>(null);
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
      <B2CPageHeader title="Messages" subtitle="What people have written to the platform." />

      {state.data ? (
        <B2CHero
          title={waitingHeadline(
            state.data.filter((message) => !message.handled_at).length,
            pages.hasMore,
          )}
        >
          Replies go to the sender&apos;s inbox in the app.
        </B2CHero>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <B2CSegmentedTabs
          items={KIND_TABS}
          value={kind}
          onChange={(next) => {
            setKind(next);
            setOpened(null);
          }}
          compact
          aria-label="Message kind"
        />
        <Checkbox
          label="Show handled"
          checked={showHandled}
          onChange={(event) => setShowHandled(event.target.checked)}
        />
      </div>
      {opened ? (
        <MessageCard
          key={opened.id}
          message={opened}
          onChanged={state.reload}
          onClose={() => setOpened(null)}
        />
      ) : null}
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
          <>
            <B2CGroupedSection eyebrow="Messages">
              {items.map((message) => (
                <B2CGroupedRow
                  key={message.id}
                  active={opened?.id === message.id}
                  onClick={() => setOpened(message)}
                  title={subjectOf(message)}
                  meta={`${kindLabel(message)} · ${senderOf(message)} · ${formatDay(message.created_at)}${
                    message.source ? ` · ${messageSourceLabel(message.source)}` : ""
                  }`}
                  trailing={message.handled_at ? <Badge tone="neutral">Handled</Badge> : undefined}
                />
              ))}
            </B2CGroupedSection>
            <LoadMore
              hasMore={pages.hasMore}
              busy={pages.loadingMore}
              onLoad={pages.loadMore}
              error={pages.moreError}
            />
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
