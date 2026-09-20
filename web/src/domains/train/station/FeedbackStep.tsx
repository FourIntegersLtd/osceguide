"use client";

import { useState } from "react";
import {
  HiOutlineArrowPath,
  HiOutlineClock,
  HiOutlineInformationCircle,
  HiOutlinePresentationChartLine,
} from "react-icons/hi2";
import { HiMicrophone } from "react-icons/hi";
import {
  Alert,
  B2CSegmentedTabs,
  Modal,
  ModalContent,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { AttemptFeedback, readResults, readTranscript } from "@/capabilities/feedback";
import { DebriefHistory, DebriefChooseModal } from "@/capabilities/debrief";
import { DebriefTips } from "@/capabilities/debrief/DebriefInformation";
import { type AttemptBrief, type AttemptReview } from "@/capabilities/attempt-runner";
import { FeedbackHistory } from "./FeedbackHistory";
import { b2cIconButton } from "@/foundation/ui/productTokens";

type FeedbackTab = "latest" | "history" | "debriefs";

const TABS: B2CSegmentedTabItem<FeedbackTab>[] = [
  {
    id: "latest",
    label: (
      <span className="inline-flex items-center gap-1.5">
        <HiOutlinePresentationChartLine className="h-4 w-4" aria-hidden />
        <span className="sm:hidden">Latest</span>
        <span className="hidden sm:inline">Latest Feedback</span>
      </span>
    ),
  },
  {
    id: "history",
    label: (
      <span className="inline-flex items-center gap-1.5">
        <HiOutlineClock className="h-4 w-4" aria-hidden />
        <span className="sm:hidden">History</span>
        <span className="hidden sm:inline">Feedback History</span>
      </span>
    ),
  },
  {
    id: "debriefs",
    label: (
      <span className="inline-flex items-center gap-1.5">
        <HiMicrophone className="h-4 w-4" aria-hidden />
        <span className="sm:hidden">Debriefs</span>
        <span className="hidden sm:inline">Debrief History</span>
      </span>
    ),
  },
];

export function FeedbackStep({
  attemptId,
  examCode,
  setId,
  entryId,
  stationVersionId,
  brief,
  review,
}: {
  attemptId: string | null;
  examCode: string;
  setId: string | null;
  entryId: string | null;
  stationVersionId: string | null;
  brief: AttemptBrief | null;
  review: AttemptReview | null;
}) {
  const [tab, setTab] = useState<FeedbackTab>("latest");
  const [explaining, setExplaining] = useState(false);
  const [debriefOpen, setDebriefOpen] = useState(false);
  const [loadingDebrief, setLoadingDebrief] = useState(false);
  const toast = useToast();

  const hasFeedback = useAsync(
    (signal) => (attemptId ? readResults(attemptId, signal) : Promise.resolve([])),
    [attemptId],
  );
  const marked = (hasFeedback.data?.length ?? 0) > 0;

  if (!attemptId) {
    return <Alert tone="info">Sit this station to get feedback on it.</Alert>;
  }

  const openDebrief = async () => {
    if (!marked || loadingDebrief) return;
    setLoadingDebrief(true);
    try {
      const transcript = await readTranscript(attemptId);
      if (transcript.messages.length === 0) {
        toast.show({
          tone: "info",
          title: "No consultation to debrief yet",
          message: "A debrief needs a recorded consultation for this station. Attempt the station first.",
        });
        return;
      }
      setDebriefOpen(true);
    } catch (cause) {
      toast.show({
        tone: "error",
        title: "We couldn't check your consultation",
        message: errorMessage(cause),
      });
    } finally {
      setLoadingDebrief(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="mb-3 flex w-full flex-wrap items-center gap-2 sm:mb-4 sm:justify-end">
        {marked && (
          <>
            <button
              type="button"
              onClick={openDebrief}
              disabled={loadingDebrief}
              className="inline-flex w-full min-w-0 items-center justify-center gap-2 rounded-lg bg-osce-accent px-4 py-2.5 text-osce-body font-medium text-white hover:bg-osce-accent-hover disabled:opacity-60 sm:w-auto sm:min-w-[11rem]"
            >
              {loadingDebrief ? (
                <HiOutlineArrowPath className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <>
                  <HiMicrophone className="h-4 w-4" aria-hidden />
                  <span>Start Debrief</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => setExplaining(true)}
              className={b2cIconButton}
              aria-label="How debrief works"
            >
              <HiOutlineInformationCircle className="h-5 w-5" />
            </button>
          </>
        )}
      </div>

      <B2CSegmentedTabs
        className="mb-4"
        items={TABS}
        value={tab}
        onChange={setTab}
        aria-label="Feedback sections"
      />

      {tab === "latest" && <AttemptFeedback attemptId={attemptId} showLiveCoverage />}
      {tab === "history" && (
        <FeedbackHistory stationVersionId={stationVersionId} entryId={entryId} stationName={brief?.station_title ?? review?.station_title ?? "this station"} />
      )}
      {tab === "debriefs" && <DebriefHistory attemptId={attemptId} stationVersionId={stationVersionId} entryId={entryId} />}

      {debriefOpen && (
        <DebriefChooseModal
          examCode={examCode}
          setId={setId}
          entryId={entryId}
          attemptId={attemptId}
          brief={brief}
          review={review}
          onClose={() => setDebriefOpen(false)}
        />
      )}

      {explaining && (
        <DebriefAboutModal examCode={examCode} onClose={() => setExplaining(false)} />
      )}
    </div>
  );
}

function DebriefAboutModal({ examCode, onClose }: { examCode: string; onClose: () => void }) {
  return (
    <Modal width="900px" height="fit-content" onClose={onClose} title="How debrief works">
      <ModalContent>
        <DebriefTips examCode={examCode} />
      </ModalContent>
    </Modal>
  );
}
