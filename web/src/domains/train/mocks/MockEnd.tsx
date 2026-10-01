"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AiOutlineLoading3Quarters } from "react-icons/ai";
import { HiArrowRight } from "react-icons/hi";
import { HiOutlineCheckCircle, HiOutlinePlus, HiOutlineUsers } from "react-icons/hi2";
import { LuTrophy } from "react-icons/lu";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  cn,
  productTokens,
} from "@/foundation/ui";
import { useAsync, useMeEvents } from "@/foundation/hooks";
import { MilestoneCelebration } from "@/domains/train/mocks/MilestoneCelebration";
import { StationOutcomes } from "@/domains/train/mocks/StationOutcomes";
import { useCurrentExam, offersPatientPractice } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { listMyAttempts, type AttemptHistoryItem } from "@/capabilities/attempt-runner";
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

/**
 * The end of a session: the retiring client's `/mocks/[mockId]/complete`.
 *
 * One card says well done, which stations are still being marked, which have
 * feedback, and how far this person has come; an SCA candidate gets a second
 * card offering a colleague to practise with.
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
        ...entries.map((entry) =>
          listMyAttempts({ setEntryId: entry.id, limit: 5 }, signal).catch(() => ({
            items: [] as AttemptHistoryItem[],
          })),
        ),
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
    <div className="w-full py-6 sm:py-8">
      <AsyncBoundary state={state}>
        {({ rows, stationsCompleted }) => {
          const markingRows = rows.filter((row) => row.feedback === "marking");
          const readyRows = rows.filter(
            (row) => row.feedback === "review" && seenMarking.has(row.entryId),
          );
          const badgeCount = checkMilestone(stationsCompleted, 0).stationBadges;
          return (
            <div className="mx-auto w-4/5 space-y-4">
              <MilestoneCelebration stationsCompleted={stationsCompleted} />
              <div className="space-y-4">
                <B2CPanelCard className="mt-0">
                  <B2CPanelCardBody className="space-y-5 p-5 sm:p-6">
                    <div className="space-y-2">
                      <p className={productTokens.b2cEyebrow}>Session completed</p>
                      <h1
                        className={cn(
                          productTokens.b2cPageTitle,
                          "inline-flex items-center gap-2.5 text-osce-heading",
                        )}
                      >
                        <LuTrophy
                          className="h-7 w-7 shrink-0 text-osce-accent sm:h-8 sm:w-8"
                          aria-hidden
                        />
                        Well done
                      </h1>
                      <p className="max-w-md text-osce-body text-b2c-text-muted">
                        Review this session while it&apos;s fresh, then keep the momentum going.
                      </p>
                    </div>

                    {(markingRows.length > 0 || readyRows.length > 0) && (
                      <ul
                        aria-label="Feedback status"
                        className="space-y-2 border-t border-b2c-border pt-4"
                      >
                        {markingRows.map((row) => (
                          <li
                            key={row.entryId}
                            className="flex items-center gap-2.5 text-osce-body text-b2c-text-secondary"
                          >
                            <AiOutlineLoading3Quarters
                              className="h-4 w-4 shrink-0 animate-spin text-osce-accent"
                              aria-hidden
                            />
                            <span>
                              Marking {row.label}… we&apos;ll let you know when it&apos;s ready.
                            </span>
                          </li>
                        ))}
                        {readyRows.map((row) => (
                          <li
                            key={row.entryId}
                            className="flex flex-wrap items-center justify-between gap-2 text-osce-body text-b2c-text-secondary"
                          >
                            <span className="inline-flex items-center gap-2.5">
                              <HiOutlineCheckCircle
                                className="h-4 w-4 shrink-0 text-osce-success-text"
                                aria-hidden
                              />
                              {row.label} feedback is ready
                            </span>
                            <button
                              type="button"
                              onClick={() => router.push(feedbackHref(row.entryId))}
                              className="inline-flex items-center gap-1 font-semibold text-osce-accent hover:underline"
                            >
                              Review feedback
                              <HiArrowRight className="h-4 w-4" aria-hidden />
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}

                    {/* A station already listed above (marking, or just marked) is not listed twice. */}
                    <StationOutcomes
                      rows={rows.filter((row) => !markingRows.includes(row) && !readyRows.includes(row))}
                      feedbackHref={feedbackHref}
                    />

                    {(stationsCompleted > 0 || badgeCount > 0) && (
                      <div className="flex flex-wrap gap-x-6 gap-y-2 border-t border-b2c-border pt-4 text-osce-body">
                        <p className="text-b2c-text-secondary">
                          <span className="font-semibold tabular-nums text-osce-ink-900">
                            {stationsCompleted}
                          </span>{" "}
                          stations completed
                        </p>
                        <p className="text-b2c-text-secondary">
                          <span className="font-semibold tabular-nums text-osce-ink-900">
                            {badgeCount}
                          </span>{" "}
                          milestone badges
                        </p>
                      </div>
                    )}
                  </B2CPanelCardBody>
                  <B2CPanelCardFooter>
                    <button
                      type="button"
                      onClick={() => router.push(hrefFor("/mocks"))}
                      className={cn(productTokens.b2cGhostButton, "justify-center gap-2")}
                    >
                      <HiOutlinePlus className="h-4 w-4" aria-hidden />
                      New session
                    </button>
                    <button
                      type="button"
                      onClick={() => router.push(hrefFor(`/mocks/${setId}`))}
                      className={cn(productTokens.b2cButtonPrimary, "justify-center gap-2")}
                    >
                      Review session
                      <HiArrowRight className="h-4 w-4" aria-hidden />
                    </button>
                  </B2CPanelCardFooter>
                </B2CPanelCard>

                {offersPeerPractice && peers ? (
                  <B2CPanelCard className="mt-0">
                    <B2CPanelCardHeader>
                      <HiOutlineUsers className="h-4 w-4 text-osce-accent" aria-hidden />
                      Keep practising
                    </B2CPanelCardHeader>
                    <B2CPanelCardBody>
                      <PracticeOptionCards
                        variant="inline"
                        onLivePractice={() => void handleJoinQueue()}
                        onSchedulePractice={() => router.push(hrefFor("/marketplace"))}
                        isJoiningQueue={isJoiningQueue || peers.queue.phase === "joining"}
                        livePracticeLabel="Live Practice"
                        schedulePracticeLabel="Schedule Practice"
                        livePracticeActionLabel="Start Now"
                        schedulePracticeActionLabel="Browse Marketplace"
                      />
                    </B2CPanelCardBody>
                  </B2CPanelCard>
                ) : null}
              </div>
            </div>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}
