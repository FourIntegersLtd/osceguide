"use client";

import { useState } from "react";
import { HiOutlineInformationCircle } from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  B2CSegmentedTabs,
  Modal,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { AttemptFeedback } from "@/capabilities/feedback";
import { DebriefHistory, DebriefLauncher } from "@/capabilities/debrief";
import { listMyAttempts } from "@/capabilities/attempt-runner";

type FeedbackTab = "latest" | "history" | "debriefs";

const TABS: B2CSegmentedTabItem<FeedbackTab>[] = [
  { id: "latest", label: "Latest Feedback" },
  { id: "history", label: "Feedback History" },
  { id: "debriefs", label: "Debrief History" },
];

/**
 * The marking, the ones before it, and the conversations about them.
 *
 * The retiring client's `FeedbackCore`: a Start Debrief button with an
 * information modal beside it, then three tabs. The feedback body itself is
 * the shared capability — domains, categories, clinical analysis, priority
 * areas, in that order — because an examiner reads the same thing.
 *
 * "Practice as Patient" is not here. On the platform that is a practice
 * session rather than a debrief, so it belongs with peer practice; see
 * `docs/port-gaps.md`.
 */
export function FeedbackStep({
  attemptId,
  examCode,
  setId,
  entryId,
  stationVersionId,
}: {
  attemptId: string | null;
  examCode: string;
  setId: string | null;
  entryId: string | null;
  stationVersionId: string | null;
}) {
  const [tab, setTab] = useState<FeedbackTab>("latest");
  const [explaining, setExplaining] = useState(false);

  if (!attemptId) {
    return <Alert tone="info">Sit this station to get feedback on it.</Alert>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-end gap-2">
        {/*
         * A debrief is started from its station set's entry — the only route
         * the backend has. A station sat as free practice therefore cannot be
         * debriefed at all; see `docs/port-gaps.md`.
         */}
        {setId && entryId && <DebriefLauncher setId={setId} entryId={entryId} />}
        <button
          type="button"
          onClick={() => setExplaining(true)}
          aria-label="What is a debrief?"
          className="text-b2c-text-muted hover:text-osce-ink-900"
        >
          <HiOutlineInformationCircle className="h-5 w-5" aria-hidden />
        </button>
      </div>

      <B2CSegmentedTabs items={TABS} value={tab} onChange={setTab} aria-label="Feedback" />

      {tab === "latest" && <AttemptFeedback attemptId={attemptId} />}
      {tab === "history" && (
        <FeedbackHistory current={attemptId} stationVersionId={stationVersionId} />
      )}
      {tab === "debriefs" && <DebriefHistory attemptId={attemptId} />}

      {explaining && <DebriefTips examCode={examCode} onClose={() => setExplaining(false)} />}
    </div>
  );
}

/** Every marked attempt at this station, so progress is visible across goes. */
function FeedbackHistory({
  current,
  stationVersionId,
}: {
  current: string;
  stationVersionId: string | null;
}) {
  const { hrefFor } = useSurface();
  const state = useAsync(
    (signal) =>
      stationVersionId
        ? listMyAttempts({ stationVersionId, limit: 25 }, signal)
        : Promise.resolve({ items: [] }),
    [stationVersionId],
  );

  return (
    <AsyncBoundary state={state}>
      {(page) => {
        const marked = page.items.filter((item) => item.has_result);
        if (marked.length === 0) {
          return <Alert tone="info">This is your first marked attempt at this station.</Alert>;
        }
        return (
          <ul className="divide-y divide-b2c-border rounded-xl border border-b2c-border">
            {marked.map((item) => (
              <li key={item.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <span className="text-osce-body text-osce-ink-900">
                  {new Date(item.created_at).toLocaleDateString("en-GB", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                  {item.id === current && (
                    <span className="ml-2 text-osce-meta text-b2c-text-muted">(this one)</span>
                  )}
                </span>
                {item.id !== current && (
                  <a
                    href={`${hrefFor(`/attempts/${item.id}`)}`}
                    className="text-osce-body text-osce-accent hover:text-osce-accent-hover"
                  >
                    View Details
                  </a>
                )}
              </li>
            ))}
          </ul>
        );
      }}
    </AsyncBoundary>
  );
}

/**
 * What a debrief is, before somebody starts their first.
 *
 * The retiring client's `DebriefTips`, which exists because "debrief" sounds
 * like written feedback and is not: it is a spoken conversation with the tutor
 * about the consultation that just happened.
 */
function DebriefTips({ examCode, onClose }: { examCode: string; onClose: () => void }) {
  return (
    <Modal onClose={onClose} width="min(95vw, 34rem)" height="fit-content">
      <div className="space-y-4 p-6">
        <h2 className="text-osce-h3 font-semibold text-osce-ink-900">About your debrief</h2>
        <ul className="space-y-3 text-osce-body text-b2c-text-muted">
          <li>
            <span className="font-medium text-osce-ink-900">Live analysis.</span> Athena has read
            your transcript and the marking, and can point at the moments that earned them.
          </li>
          <li>
            <span className="font-medium text-osce-ink-900">Targeted tips.</span> Ask why a
            competency was rated as it was, and what a stronger answer would have sounded like.
          </li>
          <li>
            <span className="font-medium text-osce-ink-900">Active practice.</span> Rehearse the
            part you fumbled — the explanation, the safety net — out loud, then and there.
          </li>
        </ul>
        {examCode === "sca" && (
          <p className="text-osce-meta text-b2c-text-muted">
            It is a conversation, so speaking to it works better than asking one question and
            listening.
          </p>
        )}
      </div>
    </Modal>
  );
}
