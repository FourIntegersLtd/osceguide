"use client";

import { Fragment, useCallback, useState } from "react";
import { AiFillLike, AiOutlineLike } from "react-icons/ai";
import { HiOutlineTrash } from "react-icons/hi2";
import { cn, linkifyOptions } from "@/foundation/ui";
import { useSession } from "@/foundation/session";
import { like, unlike, type Post } from "@/capabilities/community/api";

/**
 * The parts every community screen repeats: who wrote it, when, the like
 * toggle and the author's own delete.
 *
 * Four screens drew these by hand in the retiring client and the markup had
 * already drifted — one of them showed a like count that never came back from
 * the server.
 */

/** Naive ISO strings from the API are UTC, like Python's `utcnow().isoformat()`. */
function apiDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const raw = String(iso).trim();
  const hasZone = /[zZ]$/.test(raw) || /[+-]\d{2}:?\d{2}$/.test(raw);
  const parsed = new Date(hasZone || !raw.includes("T") ? raw : `${raw}Z`);
  return Number.isFinite(parsed.getTime()) ? parsed : null;
}

export function formatPostedDate(iso: string | null | undefined): string {
  return apiDate(iso)?.toLocaleDateString() ?? "";
}

export function formatPostedAt(iso: string | null | undefined): string {
  return apiDate(iso)?.toLocaleString() ?? "";
}

/** The signed-in person, as these screens need them. */
export function useViewer(): { id: string | null; name: string } {
  const { session } = useSession();
  return { id: session?.user.id ?? null, name: session?.user.name ?? "you" };
}

/**
 * `@somebody`.
 *
 * `PostRead` carries an author id and no name, so a stranger reads as
 * "@a colleague" until the backend serves one — see `docs/port-gaps.md`.
 */
export function authorLabel(post: Post, viewerId: string | null, viewerName: string): string {
  return post.author_id === viewerId ? `@${viewerName}` : "@a colleague";
}

const URL_PATTERN = /(https?:\/\/[^\s]+|www\.[^\s]+)/gi;

/**
 * Text with its links clickable.
 *
 * The old screens ran `linkify-react` over a post's body. The options are the
 * foundation's, so a link looks the same here as everywhere else; the
 * splitting is local because a dependency for one regex is not worth asking
 * for.
 */
export function LinkedText({ children }: { children: string }) {
  // One capture group, so `split` puts every match at an odd index. Testing
  // the pattern again would be wrong as well as redundant: it is global, and a
  // global regex carries `lastIndex` between calls.
  const parts = children.split(URL_PATTERN);
  return (
    <>
      {parts.map((part, index) =>
        index % 2 === 1 ? (
          <a
            key={index}
            href={part.startsWith("www.") ? `https://${part}` : part}
            target={linkifyOptions.target}
            rel={linkifyOptions.rel}
            className={linkifyOptions.className}
          >
            {part}
          </a>
        ) : (
          <Fragment key={index}>{part}</Fragment>
        ),
      )}
    </>
  );
}

/**
 * Like, and un-like.
 *
 * The server owns the count: a like is a row there, so the number it answers
 * with is the truth and a double tap cannot double count.
 */
export function LikeButton({
  post,
  onChanged,
  onFailed,
}: {
  post: Post;
  onChanged: (post: Post) => void;
  onFailed?: (error: unknown) => void;
}) {
  const [pending, setPending] = useState(false);
  const { id: viewerId } = useViewer();

  const toggle = useCallback(async () => {
    if (pending) return;
    setPending(true);
    try {
      onChanged(await (post.liked_by_me ? unlike(post.id) : like(post.id)));
    } catch (cause) {
      onFailed?.(cause);
    } finally {
      setPending(false);
    }
  }, [pending, post.id, post.liked_by_me, onChanged, onFailed]);

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={!viewerId || pending}
      className={cn(
        "inline-flex min-h-9 items-center gap-1.5 rounded-md px-3 text-osce-body font-medium transition",
        post.liked_by_me
          ? "bg-osce-accent !text-white"
          : "border border-osce-border bg-white text-osce-ink-600 hover:bg-b2c-surface-muted",
      )}
    >
      {post.liked_by_me ? <AiFillLike className="h-4 w-4" /> : <AiOutlineLike className="h-4 w-4" />}
      {post.like_count} Likes
    </button>
  );
}

export function DeleteButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="inline-flex min-h-9 items-center gap-1.5 rounded-md border border-osce-danger-border bg-white px-3 text-osce-body font-medium text-osce-danger transition hover:bg-osce-danger-bg"
    >
      <HiOutlineTrash className="h-3.5 w-3.5" />
      Delete
    </button>
  );
}

/** The one field shape the composer and the answer form share. */
export const fieldClass =
  "w-full rounded-md border border-osce-border bg-white px-3 py-2.5 text-osce-body text-osce-ink-900 placeholder:text-osce-ink-400 focus:border-osce-accent focus:outline-none focus:ring-2 focus:ring-osce-accent-subtle";

/**
 * A question's title.
 *
 * The retiring composer posted a body and nothing else; `platform-api` takes a
 * title beside it. Rather than put a second box in front of somebody who is
 * used to one, the first line stands in as the title — recorded in
 * `docs/port-gaps.md` as the shape disagreement it is.
 */
export function titleFromBody(body: string): string {
  const firstLine = body.trim().split("\n")[0]?.trim() ?? "";
  return firstLine.length > 120 ? `${firstLine.slice(0, 117)}…` : firstLine;
}
