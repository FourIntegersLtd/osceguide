"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { B2CPageHeader, B2CSegmentedTabs, Spinner, type B2CSegmentedTabItem } from "@/foundation/ui";
import { QuestionList } from "@/capabilities/community/QuestionList";
import { QuestionDetail } from "@/capabilities/community/QuestionDetail";
import { MyAnswers } from "@/capabilities/community/MyAnswers";
import { MyQuestions } from "@/capabilities/community/MyQuestions";
import { useRoom, useRoomName } from "@/capabilities/community/useRoom";

type CommunityTab = "allQuestions" | "myQuestions" | "myAnswers";

const COMMUNITY_TABS: B2CSegmentedTabItem<CommunityTab>[] = [
  { id: "allQuestions", label: "All questions" },
  { id: "myQuestions", label: "My questions" },
  { id: "myAnswers", label: "My answers" },
];

/**
 * Discussion, scoped by whoever is looking.
 *
 * The same three tabs an exam candidate has always had, and the same screens
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
  const [activeTab, setActiveTab] = useState<CommunityTab>("allQuestions");
  const room = useRoom(orgId);
  const roomName = useRoomName();
  const questionId = useSearchParams().get("question");

  if (questionId) return <QuestionDetail questionId={questionId} />;

  return (
    <div className="w-full">
      <B2CPageHeader
        title="Community"
        subtitle={roomName ? `Questions asked inside ${roomName}.` : undefined}
      />

      <B2CSegmentedTabs
        items={COMMUNITY_TABS}
        value={activeTab}
        onChange={setActiveTab}
        aria-label="Community"
      />

      <div id={`tab-panel-${activeTab}`} role="tabpanel">
        {activeTab === "myQuestions" ? <MyQuestions room={room} /> : null}
        {activeTab === "myAnswers" ? <MyAnswers /> : null}
        {activeTab === "allQuestions" ? <QuestionList room={room} roomName={roomName} /> : null}
      </div>
    </div>
  );
}
