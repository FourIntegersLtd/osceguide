"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Back, B2CErrorState, ConfirmModal, Spinner, cn, productTokens } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { listReplies, readQuestion, removePost, type Post } from "@/capabilities/community/api";
import { authorLabel, sortReplies, type ReplyOrder } from "@/capabilities/community/discussionModel";
import { AnswerQuestion } from "@/capabilities/community/AnswerQuestion";
import {
  DeleteButton,
  LikeButton,
  LinkedText,
  QuestionTags,
  formatPostedAt,
  titleFromBody,
  useViewer,
} from "@/capabilities/community/posts";
import { b2cCard, b2cPanelDivided } from "@/foundation/ui/productTokens";

/**
 * One question and its answers.
 *
 * The thread is read by id. It used to be searched for in the page the feed
 * already served, which meant a question older than that page read as "not
 * found" and a link shared last month was a dead end — the same shape as
 * `findLibraryStation`, and now the same fix.
 */
export function QuestionDetail({ questionId }: { questionId: string }) {
  const toast = useToast();
  // A like answers with the whole post, so the toggle keeps its own copy of
  // the question rather than re-reading the thread to move one number.
  const [likedQuestion, setLikedQuestion] = useState<Post | null>(null);
  const [confirmingQuestion, setConfirmingQuestion] = useState(false);

  const thread = useAsync(
    async (signal) => {
      const [question, replies] = await Promise.all([
        readQuestion(questionId, signal),
        listReplies(questionId, signal),
      ]);
      return { question, replies: replies.items };
    },
    [questionId],
  );

  if (thread.loading && thread.data === null) {
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner />
      </div>
    );
  }

  if (thread.error) {
    return (
      <B2CErrorState
        title="We couldn't load this question"
        description={errorMessage(thread.error)}
        onRetry={thread.reload}
        secondaryAction={<Back />}
      />
    );
  }

  const loaded = thread.data?.question ?? null;
  const shown = likedQuestion?.id === loaded?.id ? (likedQuestion ?? loaded) : loaded;
  if (!shown) {
    return (
      <p className="py-8 text-center text-osce-body text-osce-ink-500">Question not found.</p>
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      <header>
        <Back />
        <p className={cn(productTokens.b2cMonoEyebrow, "mt-4")}>
          <QuestionByline question={shown} />
        </p>
        <div className="mt-1.5 flex flex-wrap items-start justify-between gap-3">
          <h1 className="min-w-0 flex-1 font-title text-osce-heading font-semibold text-osce-ink-900">
            {shown.title || titleFromBody(shown.body)}
          </h1>
          <div className="flex items-center gap-2">
            <OwnerActions post={shown} label="Delete question" onDelete={() => setConfirmingQuestion(true)} />
            <LikeButton
              post={shown}
              onChanged={setLikedQuestion}
              onFailed={(cause) => toast.error("We couldn't save your like", errorMessage(cause))}
            />
          </div>
        </div>
      </header>

      <section className={cn(b2cCard, "space-y-3 p-5")}>
        <p className="whitespace-pre-wrap break-words text-osce-body leading-relaxed text-osce-ink-800">
          <LinkedText>{shown.body}</LinkedText>
        </p>
        <QuestionTags tags={shown.tags} />
      </section>

      <AnswerQuestion questionId={questionId} onAnswerSubmitted={thread.reload} />

      <Answers replies={thread.data?.replies ?? []} onChanged={thread.reload} />

      <DeleteQuestionModal
        isOpen={confirmingQuestion}
        questionId={questionId}
        onCancel={() => setConfirmingQuestion(false)}
      />
    </div>
  );
}

function QuestionByline({ question }: { question: Post }) {
  const viewer = useViewer();
  return (
    <>
      {authorLabel(question, viewer.id, viewer.name)} · {formatPostedAt(question.created_at)}
    </>
  );
}

function OwnerActions({
  post,
  label,
  onDelete,
}: {
  post: Post;
  label: string;
  onDelete: () => void;
}) {
  const viewer = useViewer();
  if (post.author_id !== viewer.id) return null;
  return <DeleteButton label={label} onClick={onDelete} />;
}

function DeleteQuestionModal({
  isOpen,
  questionId,
  onCancel,
}: {
  isOpen: boolean;
  questionId: string;
  onCancel: () => void;
}) {
  const router = useRouter();
  const toast = useToast();
  const { hrefFor } = useSurface();

  const confirm = useCallback(async () => {
    try {
      await removePost(questionId);
      toast.success("Question deleted");
      router.push(hrefFor("/discussion"));
    } catch (cause) {
      toast.error("We couldn't delete this question", errorMessage(cause));
    } finally {
      onCancel();
    }
  }, [questionId, router, toast, hrefFor, onCancel]);

  return (
    <ConfirmModal
      isOpen={isOpen}
      onCancel={onCancel}
      onConfirm={confirm}
      title="Delete question?"
      message="Are you sure you want to delete this question?"
      confirmText="Yes, delete"
      cancelText="Cancel"
      tone="danger"
    />
  );
}

function Answers({ replies, onChanged }: { replies: Post[]; onChanged: () => void }) {
  const toast = useToast();
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);
  const [liked, setLiked] = useState<Record<string, Post>>({});
  const [order, setOrder] = useState<ReplyOrder>("newest");

  const confirmDelete = useCallback(async () => {
    if (!pendingDelete) return;
    try {
      await removePost(pendingDelete);
      toast.success("Reply deleted");
      onChanged();
    } catch (cause) {
      toast.error("We couldn't delete this reply", errorMessage(cause));
    } finally {
      setPendingDelete(null);
    }
  }, [pendingDelete, toast, onChanged]);

  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <p className={productTokens.b2cMonoEyebrow}>Replies from the community · {replies.length}</p>
        {replies.length > 1 ? (
          <select
            aria-label="Sort replies"
            value={order}
            onChange={(event) => setOrder(event.target.value as ReplyOrder)}
            className="rounded-osce-md border border-osce-border bg-transparent px-2 py-1 text-osce-meta text-osce-ink-800"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        ) : null}
      </div>

      {replies.length === 0 ? (
        <p className="rounded-osce-lg border border-dashed border-osce-border px-5 py-6 text-center text-osce-body text-b2c-text-muted">
          No replies yet. Be the first to share your thoughts.
        </p>
      ) : (
        <ul className={b2cPanelDivided}>
          {sortReplies(replies, order).map((original) => {
            const replyPost = liked[original.id] ?? original;
            return (
              <li key={replyPost.id} id={`reply-${replyPost.id}`} className="px-5 py-4">
                <p className="whitespace-pre-wrap break-words text-osce-body leading-relaxed text-osce-ink-800">
                  <LinkedText>{replyPost.body}</LinkedText>
                </p>
                <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                  <span className="text-osce-meta text-b2c-text-muted">
                    <QuestionByline question={replyPost} />
                  </span>
                  <span className="flex items-center gap-2">
                    <OwnerActions
                      post={replyPost}
                      label="Delete reply"
                      onDelete={() => setPendingDelete(replyPost.id)}
                    />
                    <LikeButton
                      post={replyPost}
                      onChanged={(updated) => setLiked((current) => ({ ...current, [updated.id]: updated }))}
                      onFailed={(cause) => toast.error("We couldn't save your like", errorMessage(cause))}
                    />
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <ConfirmModal
        isOpen={pendingDelete !== null}
        onCancel={() => setPendingDelete(null)}
        onConfirm={confirmDelete}
        title="Delete reply?"
        message="Are you sure you want to delete this reply?"
        confirmText="Yes, delete"
        cancelText="Cancel"
        tone="danger"
      />
    </section>
  );
}
