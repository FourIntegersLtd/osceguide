"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { LuTrophy } from "react-icons/lu";
import { AsyncBoundary, ButtonLink, Card, productTokens } from "@/foundation/ui";
import { useAsync, useMeEvents } from "@/foundation/hooks";
import { MilestoneCelebration } from "@/domains/train/mocks/MilestoneCelebration";
import { StationOutcomes } from "@/domains/train/mocks/StationOutcomes";
import { useCurrentExam, offersPatientPractice } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { listMyAttempts } from "@/capabilities/attempt-runner";
import { PracticeOptionCards } from "@/capabilities/peer-practice/PracticeOptions";
import { usePeerPractice } from "@/capabilities/peer-practice/PeerPracticeProvider";
import { loadStationCatalogue, readDashboard, readSet } from "@/domains/train/api";
import {
  anyStationMarking,
  checkMilestone,
  entriesInOrder,
  stationFeedbackState,
  type StationFeedbackState,
} from "@/domains/train/mocks/model";
import { B2CHero } from "@/foundation/ui/B2CHero";

/**
 * The end of a session (canvas `train-complete`): the retiring client's
 * `/mocks/[mockId]/complete`.
 *
 * A hero says well done, the outcomes list says which stations are still
 * being marked and which have feedback, two stats say how far this person has
 * come, and an SCA candidate gets a card offering a colleague to practise with.
 *
 * The old client knew what was being marked because this browser had started
 * the job. Marking is the server's here, so a station is "marking" when its
 * newest attempt has finished and has no result, and the screen polls until
 * none are. A station that finishes marking while the page is open moves to
 * the "feedback is ready" line, as the old pending-feedback list did.
 */
export function MockEnd({ setId }: { setId: string }) {
  const router = useRouter();
  const { hrefFor } = useSurface();
  const { code: examCode, settings } = useCurrentExam();
  const offersPeerPractice = offersPatientPractice(settings);
  const peers = usePeerPractice();

  const state = useAsync(
    async (signal) => {
      const set = await readSet(setId, signal);
      const entries = entriesInOrder(set);
      const [library, dashboard, ...perEntry] = await Promise.all([
        loadStationCatalogue(set.exam_code, signal),
        readDashboard(signal),
        ...entries.map((entry) => listMyAttempts({ setEntryId: entry.id, limit: 5 }, signal)),
      ]);
      const titles = new Map(library.map((station) => [station.version_id, station.title]));
      const rows = entries.map((entry, index) => {
        const title = titles.get(entry.station_version_id);
        return {
          entryId: entry.id,
          label: title ? `Station ${index + 1}: ${title}` : `Station ${index + 1}`,
          feedback: stationFeedbackState(perEntry[index]?.items ?? []),
        };
      });
      const stationsCompleted = (dashboard.progress ?? []).reduce(
        (total, progress) => total + progress.evaluated,
        0,
      );
      return { rows, stationsCompleted };
    },
    [setId],
  );

  const rowStates = useMemo<StationFeedbackState[]>(
    () => (state.data?.rows ?? []).map((row) => row.feedback),
    [state.data],
  );
  const isAnyStationStillMarking = anyStationMarking(rowStates);

  // This screen otherwise loads once: a station that is genuinely being
  // marked would never flip over to "View feedback" without a manual reload.
  // The worker publishes `attempt` when marking finishes; a `resync` (a fresh
  // connection, or the tab coming back to the foreground) re-checks too, in
  // case the event arrived while nobody was listening.
  const { reload } = state;
  useMeEvents(
    isAnyStationStillMarking ? ["attempt"] : null,
    useCallback(() => reload(), [reload]),
  );

  // Stations seen marking on this visit; once marked they are "ready". Kept
  // by adjusting state during render, React's pattern for remembering what an
  // earlier render saw.
  const [seenMarking, setSeenMarking] = useState<ReadonlySet<string>>(() => new Set());
  const newlyMarking = (state.data?.rows ?? []).filter(
    (row) => row.feedback === "marking" && !seenMarking.has(row.entryId),
  );
  if (newlyMarking.length > 0) {
    setSeenMarking(new Set([...seenMarking, ...newlyMarking.map((row) => row.entryId)]));
  }

  const [isJoiningQueue, setIsJoiningQueue] = useState(false);
  const handleJoinQueue = async () => {
    if (!peers || !examCode) return;
    setIsJoiningQueue(true);
    try {
      await peers.queue.join(examCode);
    } finally {
      setIsJoiningQueue(false);
    }
  };

  const feedbackHref = (entryId: string) =>
    `${hrefFor(`/mocks/${setId}/stations/${entryId}`)}?action=review&tab=feedback`;

  return (
    <div className={productTokens.b2cPageColumn}>
      <AsyncBoundary state={state}>
        {({ rows, stationsCompleted }) => {
          const readyIds = new Set(
            rows
              .filter((row) => row.feedback === "review" && seenMarking.has(row.entryId))
              .map((row) => row.entryId),
          );
          const badgeCount = checkMilestone(stationsCompleted, 0).stationBadges;
          return (
            <div className="mx-auto max-w-osce-page space-y-6">
              <MilestoneCelebration stationsCompleted={stationsCompleted} />

              <B2CHero
                as="h1"
                lead
                eyebrow="Session completed"
                title="Well done"
                action={
                  <>
                    <ButtonLink href={hrefFor(`/mocks/${setId}`)} variant="primary" size="md">
                      Review session
                    </ButtonLink>
                    <ButtonLink href={hrefFor("/mocks")} variant="secondary" size="md">
                      New session
                    </ButtonLink>
                  </>
                }
                aside={
                  badgeCount > 0 ? (
                    <div className="flex shrink-0 items-center gap-3 rounded-osce-lg border border-osce-border bg-osce-surface px-4 py-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-control bg-b2c-surface-muted text-osce-ink-900">
                        <LuTrophy className="h-5 w-5" aria-hidden />
                      </span>
                      <div>
                        <p className="text-osce-body font-semibold text-osce-ink-900">
                          {badgeCount} {badgeCount === 1 ? "milestone" : "milestones"}
                        </p>
                        <p className="text-osce-meta text-b2c-text-muted">
                          {stationsCompleted} stations so far
                        </p>
                      </div>
                    </div>
                  ) : null
                }
              >
                Review this session while it is fresh, then keep the momentum going.
              </B2CHero>

              <StationOutcomes rows={rows} readyIds={readyIds} feedbackHref={feedbackHref} />

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="rounded-osce-lg border border-osce-border bg-osce-surface px-5 py-4">
                  <p className="text-osce-meta text-b2c-text-muted">Stations completed</p>
                  <p className="mt-1 text-osce-title font-semibold tabular-nums text-osce-ink-900">
                    {stationsCompleted}
                  </p>
                </div>
                <div className="rounded-osce-lg border border-osce-border bg-osce-surface px-5 py-4">
                  <p className="text-osce-meta text-b2c-text-muted">Milestone badges</p>
                  <p className="mt-1 text-osce-title font-semibold tabular-nums text-osce-ink-900">
                    {badgeCount}
                  </p>
                </div>
              </div>

              {offersPeerPractice && peers ? (
                <Card
                  title="Keep practising"
                  description="Sit a station with a colleague playing the patient."
                >
                  <PracticeOptionCards
                    variant="inline"
                    onLivePractice={() => void handleJoinQueue()}
                    onSchedulePractice={() => router.push(hrefFor("/marketplace"))}
                    isJoiningQueue={isJoiningQueue || peers.queue.phase === "joining"}
                    livePracticeLabel="Live practice"
                    schedulePracticeLabel="Schedule practice"
                    livePracticeActionLabel="Start now"
                    schedulePracticeActionLabel="Browse marketplace"
                  />
                </Card>
              ) : null}
            </div>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}
