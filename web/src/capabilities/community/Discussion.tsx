"use client";

import { useCallback, useState } from "react";
import { LuHeart, LuMessageCircle } from "react-icons/lu";
import { Alert, AsyncBoundary, Badge, Button, Card, Input, PageHeader, cn } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import {
  askQuestion,
  like,
  listQuestions,
  listReplies,
  reply as postReply,
  unlike,
  type Post,
  type Visibility,
} from "@/capabilities/community/api";

/**
 * Discussion, scoped by whoever is looking.
 *
 * On Assess the surface supplies an organisation id, so trainees see their
 * institution's threads rather than the public board. The component knows only
 * that an audience exists.
 */
export function Discussion({ orgId = null }: { orgId?: string | null }) {
  const { surface } = useSurface();
  const visibility: Visibility = orgId ? "organisation" : "public";
  const [composing, setComposing] = useState(false);
  const state = useAsync(
    (signal) => listQuestions({ visibility, orgId, cursor: null }, signal),
    [visibility, orgId],
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Discussion"
        description={
          orgId
            ? "Questions from people in your organisation."
            : "Questions from candidates preparing for the same exams."
        }
        actions={
          <Button onClick={() => setComposing((open) => !open)}>
            {composing ? "Cancel" : "Ask a question"}
          </Button>
        }
      />

      {composing && (
        <Composer
          orgId={orgId}
          visibility={visibility}
          onPosted={() => {
            setComposing(false);
            state.reload();
          }}
        />
      )}

      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{
          title: "No questions yet",
          description:
            surface === "assess"
              ? "Questions asked in your organisation will appear here."
              : "Be the first to ask one.",
        }}
      >
        {(page) => (
          <ul className="flex flex-col gap-3">
            {page.items.map((question) => (
              <li key={question.id}>
                <QuestionCard question={question} />
              </li>
            ))}
          </ul>
        )}
      </AsyncBoundary>
    </div>
  );
}

function Composer({
  orgId,
  visibility,
  onPosted,
}: {
  orgId: string | null;
  visibility: Visibility;
  onPosted: () => void;
}) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const submit = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await askQuestion({ title, body, visibility, orgId });
      setTitle("");
      setBody("");
      onPosted();
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setBusy(false);
    }
  }, [title, body, visibility, orgId, onPosted]);

  return (
    <Card title="Ask a question">
      <div className="flex flex-col gap-3">
        {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
        <Input
          label="Title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="What do you want to know?"
        />
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-ink">Details</span>
          <textarea
            value={body}
            onChange={(event) => setBody(event.target.value)}
            rows={4}
            className="rounded-control border border-border-strong bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-subtle"
            placeholder="Give enough context for someone to answer well."
          />
        </label>
        <div className="flex justify-end">
          <Button onClick={submit} disabled={busy || title.trim().length === 0}>
            Post question
          </Button>
        </div>
      </div>
    </Card>
  );
}

function QuestionCard({ question }: { question: Post }) {
  const [open, setOpen] = useState(false);
  const [liked, setLiked] = useState(question.liked_by_me);
  const [likes, setLikes] = useState(question.like_count);

  const toggleLike = useCallback(async () => {
    // Optimistic, then reconciled by the next load. A like is a row server-side,
    // so a double tap cannot double count even if this races.
    const next = !liked;
    setLiked(next);
    setLikes((n) => n + (next ? 1 : -1));
    try {
      await (next ? like(question.id) : unlike(question.id));
    } catch {
      setLiked(!next);
      setLikes((n) => n + (next ? -1 : 1));
    }
  }, [liked, question.id]);

  return (
    <Card>
      <div className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-sm font-semibold text-ink">{question.title ?? "Question"}</h3>
          {question.audience.visibility !== "public" && (
            <Badge tone="neutral">{question.audience.visibility}</Badge>
          )}
        </div>
        <p className="whitespace-pre-wrap text-sm text-ink-muted">{question.body}</p>
        <div className="flex items-center gap-4 text-sm">
          <button
            type="button"
            onClick={toggleLike}
            className={cn(
              "inline-flex items-center gap-1.5",
              liked ? "text-accent" : "text-ink-muted hover:text-ink",
            )}
            aria-pressed={liked}
          >
            <LuHeart className={cn("h-4 w-4", liked && "fill-current")} aria-hidden />
            {likes}
          </button>
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="inline-flex items-center gap-1.5 text-ink-muted hover:text-ink"
          >
            <LuMessageCircle className="h-4 w-4" aria-hidden />
            {question.reply_count} {question.reply_count === 1 ? "reply" : "replies"}
          </button>
        </div>
        {open && <Replies questionId={question.id} />}
      </div>
    </Card>
  );
}

function Replies({ questionId }: { questionId: string }) {
  const state = useAsync((signal) => listReplies(questionId, signal), [questionId]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  const send = useCallback(async () => {
    setBusy(true);
    try {
      await postReply(questionId, draft);
      setDraft("");
      state.reload();
    } finally {
      setBusy(false);
    }
  }, [draft, questionId, state]);

  return (
    <div className="flex flex-col gap-3 border-t border-border pt-3">
      <AsyncBoundary state={state} isEmpty={(page) => page.items.length === 0} empty={{ title: "No replies yet" }}>
        {(page) => (
          <ul className="flex flex-col gap-2">
            {page.items.map((item) => (
              <li key={item.id} className="rounded-control bg-surface-raised px-3 py-2 text-sm text-ink-muted">
                {item.body}
              </li>
            ))}
          </ul>
        )}
      </AsyncBoundary>
      <div className="flex gap-2">
        <Input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Write a reply"
          className="flex-1"
        />
        <Button size="sm" onClick={send} disabled={busy || draft.trim().length === 0}>
          Reply
        </Button>
      </div>
    </div>
  );
}
