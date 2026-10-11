"use client";

import Link from "next/link";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  ModalContent,
  ModalHelper,
  ModalPrimaryButton,
  ModalTitle,
  cn,
  productTokens,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { listQuestions, type Post, type Room } from "@/capabilities/community/api";
import { PAGE_SIZE } from "@/capabilities/community/QuestionList";
import { tabHref } from "@/capabilities/community/discussionModel";
import { formatPostedDate } from "@/capabilities/community/posts";

const { b2cButtonPrimarySm } = productTokens;

/**
 * The questions this person asked.
 *
 * `mine=true` narrows the feed in SQL. It used to fetch the feed's first page
 * and drop the rows that were not the viewer's, which was honest but bounded:
 * somebody with a long history saw only whatever was recent enough to be on
 * page one, and had no way to tell the two apart.
 */
export function MyQuestions({ room }: { room: Room }) {
  const state = useAsync(
    async (signal) => {
      const page = await listQuestions({ room, limit: PAGE_SIZE, mine: true }, signal);
      return page.items;
    },
    [room.visibility, room.orgId],
  );

  return (
    <ModalContent className="mb-24 max-w-3xl space-y-3">
      <div>
        <ModalTitle>My Questions</ModalTitle>
        <ModalHelper>Questions you have posted in the community.</ModalHelper>
      </div>

      <AsyncBoundary state={state}>
        {(mine) =>
          mine.length === 0 ? (
            <B2CPanelCard className="mt-0">
              <B2CPanelCardHeader>No questions yet</B2CPanelCardHeader>
              <B2CPanelCardBody className="space-y-3">
                <p className="text-osce-body text-osce-ink-500">
                  You haven&apos;t posted any questions to the community.
                </p>
                <AskFirstQuestion />
              </B2CPanelCardBody>
            </B2CPanelCard>
          ) : (
            <div className="space-y-3">
              {mine.map((question) => (
                <MyQuestionRow key={question.id} question={question} />
              ))}
            </div>
          )
        }
      </AsyncBoundary>
    </ModalContent>
  );
}

function AskFirstQuestion() {
  const { hrefFor } = useSurface();
  return (
    <Link href={hrefFor(`/discussion${tabHref("all", { compose: true })}`)}>
      <ModalPrimaryButton type="button">Ask Your First Question</ModalPrimaryButton>
    </Link>
  );
}

function MyQuestionRow({ question }: { question: Post }) {
  const { hrefFor } = useSurface();
  const answers = question.reply_count;

  return (
    <Link href={hrefFor(`/discussion?question=${question.id}`)} className="block">
      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>
          {formatPostedDate(question.created_at)} · {answers}{" "}
          {answers === 1 ? "answer" : "answers"}
        </B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-3">
          <p className="text-osce-body leading-relaxed text-osce-ink-800">{question.body}</p>
          <div className="flex justify-end border-t border-osce-border-light pt-3">
            <span className={cn(b2cButtonPrimarySm, "pointer-events-none")}>View Details</span>
          </div>
        </B2CPanelCardBody>
      </B2CPanelCard>
    </Link>
  );
}
