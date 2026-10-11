"use client";

import { useState } from "react";
import { LuBell, LuMail, LuMessageSquare, LuReply } from "react-icons/lu";
import {
  AsyncBoundary,
  B2CGroupedRow,
  B2CGroupedSection,
  B2CHero,
  B2CPageHeader,
  Badge,
  Button,
  LoadMore,
  QuietCard,
} from "@/foundation/ui";
import { formatLongDate } from "@/foundation/format";
import { errorMessage, useCursorPages } from "@/foundation/hooks";
import { listMyMessages, markAllRead, markMessageRead, type InboxMessage } from "@/capabilities/inbox/api";
import { useInboxUnreadContext } from "@/capabilities/inbox/InboxUnreadContext";
import { heroHeadline, kindLabel } from "@/capabilities/inbox/model";

function kindIcon(kind: string) {
  switch (kind) {
    case "announcement":
      return LuBell;
    case "report_answer":
      return LuMessageSquare;
    case "reply":
      return LuReply;
    default:
      return LuMail;
  }
}

/** Notes, answers and announcements from the OSCE Guide team. */
export function Inbox() {
  const unread = useInboxUnreadContext();
  const pages = useCursorPages((cursor, signal) => listMyMessages({ cursor }, signal), []);
  const [opened, setOpened] = useState<InboxMessage | null>(null);
  // Ids read in this visit: the list is not refetched, so the row is told locally.
  const [readIds, setReadIds] = useState<ReadonlySet<string>>(new Set());
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const isUnread = (message: InboxMessage) => !message.read && !readIds.has(message.id);

  const open = (message: InboxMessage) => {
    setOpened(message);
    if (!isUnread(message)) return;
    setReadIds((ids) => new Set(ids).add(message.id));
    unread.decrement();
    markMessageRead(message.id).catch((cause: unknown) => {
      setFailure(errorMessage(cause));
      setReadIds((ids) => {
        const next = new Set(ids);
        next.delete(message.id);
        return next;
      });
      unread.refresh();
    });
  };

  const readAll = async (items: InboxMessage[]) => {
    setBusy(true);
    setFailure(null);
    try {
      await markAllRead();
      setReadIds(new Set(items.map((item) => item.id)));
      unread.clear();
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader title="Notifications" subtitle="Replies and news from the OSCE Guide team." />
      <AsyncBoundary
        state={pages.state}
        isEmpty={(items) => items.length === 0}
        empty={{ title: "No notifications yet", description: "Replies to your messages and news from the OSCE Guide team will appear here." }}
      >
        {(items) => (
          <>
            <B2CHero
              title={heroHeadline(unread.count)}
              action={
                unread.count > 0 ? (
                  <Button variant="secondary" size="sm" disabled={busy} onClick={() => readAll(items)}>
                    Mark all as read
                  </Button>
                ) : undefined
              }
            >
              {unread.count > 0 ? "Open a message to mark it as read." : "Nothing new since you last looked."}
            </B2CHero>
            {failure ? <p role="alert" className="text-osce-meta text-ink-muted">{failure}</p> : null}
            {opened ? (
              <QuietCard
                title={opened.subject}
                subtitle={`${opened.from_label} · ${formatLongDate(opened.created_at)}`}
                actions={
                  <Button variant="ghost" size="sm" onClick={() => setOpened(null)}>
                    Close
                  </Button>
                }
              >
                <p className="whitespace-pre-wrap text-osce-body text-ink">{opened.body}</p>
              </QuietCard>
            ) : null}
            <B2CGroupedSection eyebrow="Messages">
              {items.map((message) => (
                <B2CGroupedRow
                  key={message.id}
                  active={opened?.id === message.id}
                  onClick={() => open(message)}
                  icon={kindIcon(message.kind)}
                  title={message.subject}
                  meta={`${kindLabel(message.kind)} · ${message.from_label} · ${formatLongDate(message.created_at)}`}
                  trailing={isUnread(message) ? <Badge tone="accent">New</Badge> : undefined}
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
