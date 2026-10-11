"use client";

import { Suspense } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { B2CPageHeader, B2CSegmentedTabs, Spinner } from "@/foundation/ui";
import { useCurrentExam } from "@/foundation/session";
import { QuestionList } from "@/capabilities/community/QuestionList";
import { QuestionDetail } from "@/capabilities/community/QuestionDetail";
import { MyAnswers } from "@/capabilities/community/MyAnswers";
import { MyQuestions } from "@/capabilities/community/MyQuestions";
import { useRoom, useRoomName } from "@/capabilities/community/useRoom";
import { COMMUNITY_TABS, parseTab, tabHref, type CommunityTab } from "@/capabilities/community/discussionModel";

const COMMUNITY_COPY =
  "Ask anything about OSCE Guide, your exam or skills training. Other members and the OSCE Guide assistant answer.";

/**
 * Discussion, scoped by whoever is looking.
 *
 * The same four tabs (in the URL as `?tab=`) an exam candidate has always had, and the same screens
 * an institution gets: the backend addresses every post to everybody, to one
 * organisation or to one group, so a cohort's private conversation is this
 * component with a different audience rather than a second implementation.
 * Which audience is `useRoom()` — the workspace from `useSurface()`, turned
 * into the organisation's id — and nothing here knows what an institution is.
 *
 * `orgId` overrides it for a caller that already resolved the organisation
 * itself; nothing else about an arm reaches in.
 */
export function Discussion({ orgId = null }: { orgId?: string | null }) {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-16">
          <Spinner />
        </div>
      }
    >
      <CommunityCore orgId={orgId} />
    </Suspense>
  );
}

/**
 * One question opens at `?question=<id>` rather than on its own route: the
 * capability owns a single page on every surface that mounts it, and a link
 * somebody sends a colleague still opens the thread.
 */
function CommunityCore({ orgId }: { orgId: string | null }) {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const room = useRoom(orgId);
  const roomName = useRoomName();
  const { code: examCode } = useCurrentExam();
  const questionId = params.get("question");
  const activeTab = parseTab(params.get("tab"));
  const setActiveTab = (tab: CommunityTab) => router.replace(`${pathname}${tabHref(tab)}`);

  if (questionId) return <QuestionDetail questionId={questionId} />;

  return (
    <div className="w-full">
      <B2CPageHeader
        title="Community"
        subtitle={roomName ? `Questions asked inside ${roomName}.` : COMMUNITY_COPY}
      />

      <B2CSegmentedTabs
        items={COMMUNITY_TABS}
        value={activeTab}
        onChange={setActiveTab}
        aria-label="Community"
      />

      <div id={`tab-panel-${activeTab}`} role="tabpanel">
        {activeTab === "questions" ? <MyQuestions room={room} /> : null}
        {activeTab === "answers" ? <MyAnswers /> : null}
        {activeTab === "all" ? (
          <QuestionList room={room} roomName={roomName} compose={params.get("compose") === "1"} />
        ) : null}
        {activeTab === "exam" ? <QuestionList room={room} roomName={roomName} examCode={examCode} /> : null}
      </div>
    </div>
  );
}
