"use client";

import Link from "next/link";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  ModalContent,
  ModalHelper,
  ModalSecondaryButton,
  ModalTitle,
  cn,
  productTokens,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { listMyAnswers, type Post } from "@/capabilities/community/api";
import { PAGE_SIZE } from "@/capabilities/community/QuestionList";
import { formatPostedDate } from "@/capabilities/community/posts";

const { b2cButtonPrimarySm } = productTokens;

/**
 * The answers this person wrote.
 *
 * `GET /community/replies?author=me` is what made this screen possible. Until
 * it existed, replies were only readable one question at a time, so assembling
 * the tab meant a request per question in the feed — and the screen shipped as
 * the empty state below, however many answers the person had written. The
 * placeholder was the right call at the time; keeping it now would not be.
 */
export function MyAnswers() {
  const { hrefFor } = useSurface();
  const state = useAsync(
    (signal) => listMyAnswers({ limit: PAGE_SIZE }, signal),
    [],
  );

  return (
    <ModalContent className="mb-24 max-w-3xl space-y-3">
      <div>
        <ModalTitle>My Answers</ModalTitle>
        <ModalHelper>Answers you have contributed to the community.</ModalHelper>
      </div>

      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{
          title: "No answers yet",
          description: "You haven't answered any questions in the community.",
          action: (
            <Link href={hrefFor("/discussion")}>
              <ModalSecondaryButton type="button">Explore Questions</ModalSecondaryButton>
            </Link>
          ),
        }}
      >
        {(page) => (
          <div className="space-y-3">
            {page.items.map((answer) => (
              <MyAnswerRow key={answer.id} answer={answer} discussionHref={hrefFor("/discussion")} />
            ))}
          </div>
        )}
      </AsyncBoundary>
    </ModalContent>
  );
}

function MyAnswerRow({
  answer,
  discussionHref,
}: {
  answer: Post;
  discussionHref: string;
}) {
  return (
    <Link
      href={answer.parent_id ? `${discussionHref}?question=${answer.parent_id}` : discussionHref}
      className="block"
    >
      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>{formatPostedDate(answer.created_at)}</B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-3">
          <p className="text-osce-body leading-relaxed text-osce-ink-800">{answer.body}</p>
          <div className="flex justify-end border-t border-osce-border-light pt-3">
            <span className={cn(b2cButtonPrimarySm, "pointer-events-none")}>View Thread</span>
          </div>
        </B2CPanelCardBody>
      </B2CPanelCard>
    </Link>
  );
}
