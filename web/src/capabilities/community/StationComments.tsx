"use client";

import { useCallback, useState } from "react";
import { HiOutlineInformationCircle } from "react-icons/hi2";
import { AsyncBoundary, Button, Card } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import {
  commentOnStation,
  listStationComments,
  removePost,
  type Post,
} from "@/capabilities/community/api";
import { useRoom } from "@/capabilities/community/useRoom";
import {
  DeleteButton,
  LikeButton,
  LinkedText,
  authorLabel,
  formatPostedDate,
  useViewer,
} from "@/capabilities/community/posts";

/**
 * What people said about one station.
 *
 * The same `posts` table as the questions above it, with a `comment` kind and
 * a station id — which is why the retiring client's separate comments feature
 * is a component in this capability rather than a second one. It is
 * audience-scoped like everything else here, so an institution's notes on a
 * station stay inside the institution.
 *
 * The admin moderation screens beside it are deliberately not ported: removal
 * is the backend's rule now — your own, a platform moderator's, or an
 * institution's inside its own room.
 */
export function StationComments({ stationId }: { stationId: string }) {
  const room = useRoom();
  const toast = useToast();
  const [newComment, setNewComment] = useState("");
  const [isPosting, setIsPosting] = useState(false);
  const [edited, setEdited] = useState<Record<string, Post | null>>({});

  const state = useAsync(
    (signal) => listStationComments(stationId, signal),
    [stationId, room.visibility, room.orgId],
  );

  const submit = useCallback(async () => {
    if (!newComment.trim() || isPosting) return;
    setIsPosting(true);
    try {
      await commentOnStation(stationId, newComment, room);
      setNewComment("");
      setEdited({});
      state.reload();
      toast.success("Comment posted");
    } catch (cause) {
      toast.error("We couldn't post your comment", errorMessage(cause));
    } finally {
      setIsPosting(false);
    }
  }, [newComment, isPosting, stationId, room, state, toast]);

  const remove = useCallback(
    async (commentId: string) => {
      try {
        await removePost(commentId);
        setEdited((current) => ({ ...current, [commentId]: null }));
      } catch (cause) {
        toast.error("We couldn't delete this comment", errorMessage(cause));
      }
    },
    [toast],
  );

  return (
    <Card padding="md" scrollable={false} className="flex h-[600px] flex-col md:h-[600px]">
      <h3 className="mb-2 pb-2 text-osce-subheading font-semibold text-osce-ink-900 md:mb-4">
        Community Comments
      </h3>

      <div className="mb-2 flex-1 space-y-3 overflow-y-auto rounded-lg border border-b2c-border p-2 md:mb-4 md:space-y-4 md:p-4">
        <AsyncBoundary state={state}>
          {(page) => {
            const comments = page.items
              .map((item) => (item.id in edited ? edited[item.id] : item))
              .filter((item): item is Post => item !== null);
            if (comments.length === 0) {
              return (
                <p className="text-center text-b2c-text-muted">
                  No comments yet for this station. Be the first to share a tip.
                </p>
              );
            }
            return comments.map((comment) => (
              <CommentRow
                key={comment.id}
                comment={comment}
                onChanged={(next) => setEdited((current) => ({ ...current, [next.id]: next }))}
                onDelete={() => remove(comment.id)}
              />
            ));
          }}
        </AsyncBoundary>
      </div>

      <div className="mt-auto">
        <div className="flex flex-col items-stretch gap-2 md:flex-row md:items-end md:gap-3">
          <textarea
            value={newComment}
            onChange={(event) => setNewComment(event.target.value)}
            placeholder="Write a comment, share useful links, make suggestions about the management plan..."
            className="flex-1 resize-none rounded-lg border border-b2c-border px-2 py-8 text-osce-body md:p-3"
            aria-label="Your comment"
          />
          <Button
            type="button"
            variant="primary"
            size="md"
            themeType="b2c"
            onClick={submit}
            isLoading={isPosting}
            disabled={!newComment.trim()}
          >
            {isPosting ? "Posting…" : "Post"}
          </Button>
        </div>
      </div>

      <div className="my-6 flex items-center justify-center gap-1.5 px-2 md:my-4">
        <HiOutlineInformationCircle className="h-4 w-4 flex-shrink-0 text-osce-accent md:h-5 md:w-5" />
        <p className="text-center text-osce-caption leading-5 text-b2c-text-muted">
          Comments are moderated and may be removed if they violate community guidelines.
        </p>
      </div>
    </Card>
  );
}

function CommentRow({
  comment,
  onChanged,
  onDelete,
}: {
  comment: Post;
  onChanged: (post: Post) => void;
  onDelete: () => void;
}) {
  const viewer = useViewer();
  const toast = useToast();

  return (
    <div className="group rounded-lg p-2 transition-all duration-200 hover:bg-b2c-surface-muted md:p-4">
      <div className="flex flex-col justify-between gap-2 md:flex-row md:items-start md:gap-0">
        <div className="flex-1">
          <p className="text-osce-body font-semibold text-osce-ink-900 transition-colors hover:text-osce-accent-hover">
            {authorLabel(comment, viewer.id, viewer.name)}
          </p>
          <p className="text-osce-caption text-b2c-text-muted">
            {formatPostedDate(comment.created_at)}
          </p>
          <div className="mt-2 md:mt-3">
            <p className="rounded-lg bg-b2c-surface-muted p-2 text-osce-body leading-relaxed text-b2c-text-secondary md:p-3">
              <LinkedText>{comment.body}</LinkedText>
            </p>
          </div>
        </div>
        <div className="mt-2 flex items-center justify-end gap-1.5 md:mt-0">
          <LikeButton
            post={comment}
            onChanged={onChanged}
            onFailed={(cause) => toast.error("We couldn't save your like", errorMessage(cause))}
          />
          {comment.author_id === viewer.id ? (
            <DeleteButton label="Delete your comment" onClick={onDelete} />
          ) : null}
        </div>
      </div>
    </div>
  );
}
