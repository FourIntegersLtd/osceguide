"use client";

import { useState } from "react";
import {
  Alert,
  AsyncBoundary,
  B2CGroupedRow,
  B2CGroupedSection,
  B2CHero,
  B2CPageHeader,
  Badge,
  Button,
  ConfirmModal,
  Input,
  LoadMore,
  Textarea,
} from "@/foundation/ui";
import { formatLongDate } from "@/foundation/format";
import { errorMessage, useCursorPages, useToast } from "@/foundation/hooks";
import {
  listAnnouncements,
  postAnnouncement,
  withdrawAnnouncement,
  type Announcement,
} from "@/domains/platform/api";

/**
 * Things said to every learner. An announcement reaches the accounts that
 * exist when it is posted; people who sign up later do not see it. Withdrawing
 * hides it from inboxes and keeps the row here, with how many had read it.
 */
export function Announcements() {
  const toast = useToast();
  const pages = useCursorPages((cursor, signal) => listAnnouncements({ cursor }, signal), []);
  const [composing, setComposing] = useState(false);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [opened, setOpened] = useState<Announcement | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stopComposing = () => {
    setComposing(false);
    setConfirming(false);
    setSubject("");
    setBody("");
    setError(null);
  };

  const post = async () => {
    setBusy(true);
    setError(null);
    try {
      await postAnnouncement({ subject: subject.trim(), body: body.trim() });
      toast.success("Announcement posted");
      stopComposing();
      pages.state.reload();
    } catch (cause) {
      setConfirming(false);
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  const withdraw = async (announcement: Announcement) => {
    setBusy(true);
    setError(null);
    try {
      await withdrawAnnouncement(announcement.id);
      toast.success("Announcement withdrawn");
      setOpened(null);
      pages.state.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader title="Announcements" subtitle="Notices that appear in every learner's inbox." />
      <B2CHero
        title="Tell every learner something"
        action={
          composing ? undefined : (
            <Button
              themeType="b2b" variant="commit"
              size="sm"
              onClick={() => {
                setOpened(null);
                setComposing(true);
              }}
            >
              New announcement
            </Button>
          )
        }
      >
        It reaches everyone with an account today. People who sign up later will not see it.
      </B2CHero>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {composing ? (
        <B2CGroupedSection
          eyebrow="New announcement"
          action={
            <span className="flex flex-wrap items-center gap-2">
              <Button
                themeType="b2b" variant="commit"
                size="sm"
                disabled={busy || !subject.trim() || !body.trim()}
                onClick={() => setConfirming(true)}
              >
                Post to everyone
              </Button>
              <Button variant="ghost" size="sm" disabled={busy} onClick={stopComposing}>
                Cancel
              </Button>
            </span>
          }
        >
          <B2CGroupedRow title="Shown in the inbox of every learner, with an unread marker." />
          <div className="flex flex-col gap-3 px-5 py-4">
            <Input label="Subject" value={subject} maxLength={200} onChange={(event) => setSubject(event.target.value)} />
            <Textarea label="Message" value={body} maxLength={5000} onChange={(event) => setBody(event.target.value)} />
          </div>
        </B2CGroupedSection>
      ) : null}
      {opened ? (
        <B2CGroupedSection
          eyebrow={opened.subject}
          action={
            <span className="flex flex-wrap items-center gap-2">
              {opened.withdrawn_at ? null : (
                <Button variant="ghost" size="sm" disabled={busy} onClick={() => withdraw(opened)}>
                  Withdraw
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={() => setOpened(null)}>
                Close
              </Button>
            </span>
          }
        >
          <B2CGroupedRow title={`${opened.sender_name ?? "OSCE Guide team"} · ${formatLongDate(opened.created_at)} · seen by ${opened.read_count}`} />
          <div className="flex flex-col gap-3 px-5 py-4">
            <p className="whitespace-pre-wrap text-osce-body text-ink">{opened.body}</p>
          </div>
        </B2CGroupedSection>
      ) : null}
      <AsyncBoundary
        state={pages.state}
        isEmpty={(items) => items.length === 0}
        empty={{ title: "Nothing posted yet", description: "Announcements you post will be listed here." }}
      >
        {(items) => (
          <>
            <B2CGroupedSection eyebrow="Posted">
              {items.map((announcement) => (
                <B2CGroupedRow
                  key={announcement.id}
                  active={opened?.id === announcement.id}
                  onClick={() => {
                    setComposing(false);
                    setOpened(announcement);
                  }}
                  title={announcement.subject}
                  meta={`${announcement.sender_name ?? "OSCE Guide team"} · ${formatLongDate(announcement.created_at)} · seen by ${announcement.read_count}`}
                  trailing={announcement.withdrawn_at ? <Badge tone="neutral">Withdrawn</Badge> : undefined}
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
      <ConfirmModal
        isOpen={confirming}
        onCancel={() => setConfirming(false)}
        onConfirm={() => post()}
        isLoading={busy}
        error={null}
        title="Post to every learner?"
        confirmText="Post to everyone"
        message="Everyone with an account will see this in their inbox. You can withdraw it later, but anyone who has already read it keeps having read it."
      />
    </div>
  );
}
