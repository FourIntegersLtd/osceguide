"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Back,
  B2CErrorState,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  ConfirmModal,
  ModalContent,
  ModalHelper,
  ModalTitle,
  Spinner,
} from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { listQuestions, listReplies, removePost, type Post, type Room } from "@/capabilities/community/api";
import { AnswerQuestion } from "@/capabilities/community/AnswerQuestion";
import { PAGE_SIZE } from "@/capabilities/community/QuestionList";
import {
  DeleteButton,
  LikeButton,
  LinkedText,
  authorLabel,
  formatPostedAt,
  useViewer,
} from "@/capabilities/community/posts";

/**
 * One question and its answers.
 *
 * `platform-api` has no read for a single question — only the paged list — so
 * the thread is found in the page the feed already serves. A question older
 * than that page reads as "not found", which is the honest answer until the
 * endpoint exists; `docs/port-gaps.md` carries it.
 */
export function QuestionDetail({ questionId, room }: { questionId: string; room: Room }) {
  const toast = useToast();
  // A like answers with the whole post, so the toggle keeps its own copy of
  // the question rather than re-reading the feed to move one number.
  const [likedQuestion, setLikedQuestion] = useState<Post | null>(null);
  const [confirmingQuestion, setConfirmingQuestion] = useState(false);

  const thread = useAsync(
    async (signal) => {
      const [page, replies] = await Promise.all([
        listQuestions({ room, limit: PAGE_SIZE }, signal),
        listReplies(questionId, signal),
      ]);
      const found = page.items.find((item) => item.id === questionId) ?? null;
      return { question: found, replies: replies.items };
    },
    [questionId, room.visibility, room.orgId],
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
    <ModalContent className="mb-24 max-w-4xl space-y-3">
      <Back />

      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>
          <QuestionByline question={shown} />
        </B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-3">
          <p className="break-words text-osce-body leading-relaxed text-osce-ink-800">
            <LinkedText>{shown.body}</LinkedText>
          </p>
          <div className="flex items-center justify-end gap-2 border-t border-osce-border-light pt-3">
            <OwnerActions post={shown} label="Delete question" onDelete={() => setConfirmingQuestion(true)} />
            <LikeButton
              post={shown}
              onChanged={setLikedQuestion}
              onFailed={(cause) =>
                toast.error("We couldn't save your like", errorMessage(cause))
              }
            />
          </div>
        </B2CPanelCardBody>
      </B2CPanelCard>

      <div className="md:grid md:grid-cols-2 md:gap-x-6 lg:gap-x-8">
        <Answers replies={thread.data?.replies ?? []} onChanged={thread.reload} />

        <div className="mt-6 md:sticky md:top-6 md:mt-0 md:self-start">
          <AnswerQuestion questionId={questionId} onAnswerSubmitted={thread.reload} />
        </div>
      </div>

      <DeleteQuestionModal
        isOpen={confirmingQuestion}
        questionId={questionId}
        onCancel={() => setConfirmingQuestion(false)}
      />
    </ModalContent>
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
    <div className="space-y-3">
      <div>
        <ModalTitle>Answers ({replies.length})</ModalTitle>
        <ModalHelper>Replies from the community.</ModalHelper>
      </div>

      {replies.length === 0 ? (
        <B2CPanelCard className="mt-0">
          <B2CPanelCardBody>
            <p className="text-osce-body text-osce-ink-500">
              No answers yet. Be the first to share your thoughts!
            </p>
          </B2CPanelCardBody>
        </B2CPanelCard>
      ) : (
        <div className="max-h-[600px] space-y-3 overflow-y-auto pr-1">
          {replies.map((original) => {
            const replyPost = liked[original.id] ?? original;
            return (
              <div key={replyPost.id} id={`reply-${replyPost.id}`}>
                <B2CPanelCard className="mt-0">
                  <B2CPanelCardHeader>
                    <QuestionByline question={replyPost} />
                  </B2CPanelCardHeader>
                  <B2CPanelCardBody className="space-y-3">
                    <p className="whitespace-pre-wrap break-words text-osce-body leading-relaxed text-osce-ink-800">
                      <LinkedText>{replyPost.body}</LinkedText>
                    </p>
                    <div className="flex items-center justify-end gap-2 border-t border-osce-border-light pt-3">
                      <OwnerActions
                        post={replyPost}
                        label="Delete reply"
                        onDelete={() => setPendingDelete(replyPost.id)}
                      />
                      <LikeButton
                        post={replyPost}
                        onChanged={(updated) =>
                          setLiked((current) => ({ ...current, [updated.id]: updated }))
                        }
                        onFailed={(cause) =>
                          toast.error("We couldn't save your like", errorMessage(cause))
                        }
                      />
                    </div>
                  </B2CPanelCardBody>
                </B2CPanelCard>
              </div>
            );
          })}
        </div>
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
    </div>
  );
}
