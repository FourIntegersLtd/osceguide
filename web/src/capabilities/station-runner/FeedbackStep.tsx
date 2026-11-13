"use client";

import { useState } from "react";
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
import { FEEDBACK_VS_DEBRIEF } from "@/capabilities/debrief/debriefCopy";
import { type AttemptBrief, type AttemptReview } from "@/capabilities/attempt-runner";
import { FeedbackHistory } from "./FeedbackHistory";
import { DebriefActions } from "./DebriefActions";

type FeedbackTab = "latest" | "history" | "debriefs";

const TABS: B2CSegmentedTabItem<FeedbackTab>[] = [
  { id: "latest", label: "Feedback" },
  { id: "history", label: "History" },
  { id: "debriefs", label: "Debriefs" },
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
  const [endedDebrief, setEndedDebrief] = useState<string | null>(null);
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
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
        <B2CSegmentedTabs
          compact
          className="min-w-0 max-w-full"
          items={TABS}
          value={tab}
          onChange={setTab}
          aria-label="Feedback sections"
        />
        <DebriefActions
          markedState={hasFeedback}
          loadingDebrief={loadingDebrief}
          onExplain={() => setExplaining(true)}
          onStart={() => openDebrief()}
        />
      </div>
      {marked ? <p className="text-osce-meta text-b2c-text-muted">{FEEDBACK_VS_DEBRIEF}</p> : null}

      {tab === "latest" && <AttemptFeedback attemptId={attemptId} showLiveCoverage showNonverbal />}
      {tab === "history" && (
        <FeedbackHistory stationVersionId={stationVersionId} entryId={entryId} stationName={brief?.station_title ?? review?.station_title ?? "this station"} />
      )}
      {tab === "debriefs" && (
        <DebriefHistory attemptId={attemptId} stationVersionId={stationVersionId} entryId={entryId}
          awaitingAttemptId={endedDebrief} />
      )}

      {debriefOpen && (
        <DebriefChooseModal
          examCode={examCode}
          setId={setId}
          entryId={entryId}
          attemptId={attemptId}
          brief={brief}
          review={review}
          onClose={() => {
            setDebriefOpen(false);
            // A debrief that has just ended is what the learner wants to see next.
            if (endedDebrief) setTab("debriefs");
          }}
          onDebriefEnded={setEndedDebrief}
        />
      )}

      {explaining && (
        <DebriefAboutModal onClose={() => setExplaining(false)} />
      )}
    </div>
  );
}

function DebriefAboutModal({ onClose }: { onClose: () => void }) {
  return (
    <Modal width="900px" height="fit-content" onClose={onClose} title="How debrief works">
      <ModalContent>
        <DebriefTips />
      </ModalContent>
    </Modal>
  );
}
