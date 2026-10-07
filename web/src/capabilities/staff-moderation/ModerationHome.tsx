"use client";

import { useState } from "react";
import {
  AsyncBoundary,
  Button,
  ConfirmModal,
  QuietCard,
  B2CGroupedRow,
  B2CGroupedSection,
  B2CHero,
  B2CPageHeader,
  LoadMore,
} from "@/foundation/ui";
import Link from "next/link";
import { PERSONAL_SLUG } from "@/foundation/routing";
import { stationHref } from "@/capabilities/stations";
import { formatLongDate, plural } from "@/foundation/format";
import { errorMessage, useCursorPages, useToast } from "@/foundation/hooks";
import {
  deleteModerationPost,
  listModerationPosts,
  type ModerationPost,
} from "@/capabilities/staff-moderation/api";

function postTitle(post: ModerationPost): string {
  return "title" in post && typeof post.title === "string" && post.title
    ? post.title
    : post.kind === "reply"
      ? "Reply"
      : "Post";
}

/** Where a moderator reads the post in context: the station for a comment, else its thread. */
function postHref(post: ModerationPost): string {
  if (post.station_id) {
    return stationHref((path) => `/app/${PERSONAL_SLUG}${path}`, post.station_id);
  }
  return `/app/${PERSONAL_SLUG}/discussion?question=${encodeURIComponent(post.parent_id ?? post.id)}`;
}

function firstLine(body: string): string {
  return body.split("\n").find((line) => line.trim() !== "")?.trim() ?? "";
}

export function ModerationHome() {
  const pages = useCursorPages(
    (cursor, signal) => listModerationPosts({ days: 7, cursor }, signal),
    [],
  );
  const state = pages.state;
  const toast = useToast();
  const [open, setOpen] = useState<ModerationPost | null>(null);
  const [target, setTarget] = useState<ModerationPost | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirmDelete = async () => {
    if (!target) return;
    setBusy(true);
    setError(null);
    try {
      await deleteModerationPost(target.id);
      toast.success("Post removed");
      setTarget(null);
      setOpen(null);
      state.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Moderation"
        subtitle="Recent community posts. Remove anything that should not stay public."
      />

      <AsyncBoundary
        state={state}
        isEmpty={(posts) => posts.length === 0}
        empty={{
          title: "Queue is empty",
          description: "No posts in the last seven days.",
        }}
      >
        {(posts) => (
          <>
            <B2CHero
              title={`${plural(posts.length, "post")}${pages.hasMore ? " so far" : ""} in the last seven days`}
            />
            {open ? (
              <QuietCard
                title={postTitle(open)}
                subtitle={`${open.author_name ?? "Someone"} · ${formatLongDate(open.created_at)}`}
                actions={
                  <>
                    <Link href={postHref(open)} target="_blank" rel="noreferrer" className="inline-flex">
                      <Button variant="ghost" size="sm">
                        Open in context
                      </Button>
                    </Link>
                    <Button variant="ghost" size="sm" onClick={() => setTarget(open)}>
                      Delete
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setOpen(null)}>
                      Close
                    </Button>
                  </>
                }
              >
                <p className="whitespace-pre-wrap text-osce-body text-ink">{open.body}</p>
              </QuietCard>
            ) : null}
            <B2CGroupedSection eyebrow="Last seven days">
              {posts.map((post) => (
                <B2CGroupedRow
                  key={post.id}
                  active={open?.id === post.id}
                  onClick={() => setOpen(post)}
                  title={postTitle(post)}
                  meta={`${post.author_name ?? "Someone"} · ${formatLongDate(post.created_at)} · ${firstLine(post.body)}`}
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
        isOpen={target !== null}
        onCancel={() => {
          setTarget(null);
          setError(null);
        }}
        onConfirm={() => confirmDelete()}
        isLoading={busy}
        error={error}
        tone="danger"
        title="Delete this post?"
        confirmText="Delete"
        message="This removes the post for everyone. It cannot be undone from here."
      />
    </div>
  );
}
