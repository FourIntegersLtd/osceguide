"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  ModalContent,
  ModalHelper,
  ModalPrimaryButton,
  ModalTitle,
  cn,
  productTokens,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { askQuestion, listQuestions, type Post, type Room } from "@/capabilities/community/api";
import { fieldClass, formatPostedDate, titleFromBody, useViewer, authorLabel } from "@/capabilities/community/posts";

const { b2cBodyText, b2cBodyTextMuted, b2cButtonPrimarySm, b2cPanelCardTitle } = productTokens;

/** One page of the feed. Questions are cursor-paginated; this is the first page. */
export const PAGE_SIZE = 100;

/**
 * Ask a question, and browse what everybody else asked.
 *
 * The list takes its audience from the workspace: a personal one asks for no
 * audience and gets the public pool plus every room the person is in; an
 * organisation's asks for that organisation and gets only its threads. The
 * composer posts into the same room, so a cohort's question is never published
 * to the world by accident.
 */
export function QuestionList({ room, roomName }: { room: Room; roomName: string | null }) {
  const state = useAsync(
    (signal) => listQuestions({ room, limit: PAGE_SIZE }, signal),
    [room.visibility, room.orgId],
  );

  return (
    <ModalContent className="mb-24 max-w-3xl space-y-3">
      <div>
        <ModalTitle>Ask a Question</ModalTitle>
        <ModalHelper>
          {roomName
            ? `Need help? Ask below to get responses from ${roomName}.`
            : "Need help? Ask below to get responses from colleagues."}
        </ModalHelper>
      </div>

      <Composer room={room} onPosted={state.reload} />

      <div className="pt-2">
        <ModalTitle>Recent Questions</ModalTitle>
        <ModalHelper>Browse what others are asking.</ModalHelper>
      </div>

      <AsyncBoundary state={state}>
        {(page) =>
          page.items.length === 0 ? (
            <B2CPanelCard className="mt-0">
              <B2CPanelCardBody>
                <p className={b2cBodyTextMuted}>
                  {roomName
                    ? `No questions in ${roomName} yet. Be the first to ask!`
                    : "No questions yet. Be the first to ask!"}
                </p>
              </B2CPanelCardBody>
            </B2CPanelCard>
          ) : (
            <div className="space-y-3">
              {page.items.map((question) => (
                <QuestionRow key={question.id} question={question} />
              ))}
            </div>
          )
        }
      </AsyncBoundary>
    </ModalContent>
  );
}

function Composer({ room, onPosted }: { room: Room; onPosted: () => void }) {
  const [content, setContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    if (!content.trim()) {
      setError("Question content cannot be empty.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await askQuestion({ title: titleFromBody(content), body: content, room });
      setContent("");
      onPosted();
    } catch (cause) {
      setError(errorMessage(cause) || "Failed to submit question. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }, [content, room, onPosted]);

  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader className={b2cPanelCardTitle}>New question</B2CPanelCardHeader>
      <B2CPanelCardBody className="space-y-4">
        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="Type your question here..."
          className={`${fieldClass} min-h-[5.5rem] resize-y`}
          rows={3}
          aria-label="Your question"
        />
        {error ? <p className={b2cBodyTextMuted}>{error}</p> : null}
      </B2CPanelCardBody>
      <B2CPanelCardFooter>
        <ModalPrimaryButton type="button" disabled={isSubmitting} onClick={submit}>
          {isSubmitting ? "Posting..." : "Post Question"}
        </ModalPrimaryButton>
      </B2CPanelCardFooter>
    </B2CPanelCard>
  );
}

function QuestionRow({ question }: { question: Post }) {
  const { hrefFor } = useSurface();
  const viewer = useViewer();
  const answers = question.reply_count;

  return (
    <Link href={hrefFor(`/discussion?question=${question.id}`)} className="block w-full text-left">
      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>
          {authorLabel(question, viewer.id, viewer.name)} · {formatPostedDate(question.created_at)} ·{" "}
          {answers} {answers === 1 ? "answer" : "answers"}
        </B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-3">
          <p className={cn(b2cBodyText, "leading-relaxed text-osce-ink-800")}>{question.body}</p>
          <div className="flex justify-end border-t border-osce-border-light pt-3">
            <span className={cn(b2cButtonPrimarySm, "pointer-events-none")}>Reply</span>
          </div>
        </B2CPanelCardBody>
      </B2CPanelCard>
    </Link>
  );
}
