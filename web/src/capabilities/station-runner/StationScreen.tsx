"use client";
import { LiveCoveragePanel } from "@/capabilities/attempt-runner/coverage/LiveCoveragePanel";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  HiOutlineArrowRight,
  HiOutlineCheckCircle,
  HiOutlineDocumentText,
  HiOutlineIdentification,
  HiOutlineMicrophone,
} from "react-icons/hi2";
import {
  Alert,
  Button,
  ConfirmModal,
  LeaveConfirmModal,
  LoadingSpinner,
  Timer,
  cn,
} from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  ConsultationPanel,
  ConsultationScreen,
  ManagementPlanView,
  StationBrief,
  consultationPatientFromBrief,
  useAttemptSession,
  usePracticeTimers,
} from "@/capabilities/attempt-runner";
import { readResults } from "@/capabilities/attempt-runner";
import { MarkingModal } from "@/capabilities/station-runner/MarkingModal";
import { FeedbackStep } from "@/capabilities/station-runner/FeedbackStep";
import { TranscriptStep } from "@/capabilities/station-runner/TranscriptStep";
import { SimulationTimeUpModal } from "@/capabilities/station-runner/SimulationTimeUpModal";
import { useStationUrl } from "@/capabilities/station-runner/useStationUrl";
import {
  STEP_LABELS,
  StationHeader,
  StationTabs,
  stepsFor,
  type ComeBackFlag,
  type StationStep,
} from "@/capabilities/station-runner/StationChrome";
import {
  forgetStationAttempt,
  useStationAttempt,
  type StationAction,
} from "@/capabilities/station-runner/useStationAttempt";
import {
  useOptionalPendingFeedback,
  feedbackReviewHref,
} from "@/capabilities/pending-feedback";

export type StationSource =
  | { kind: "set"; setId: string; entryId: string }
  | { kind: "practice"; stationId: string }
  | { kind: "self_practice"; orgSlug: string; stationId: string };

export interface StationScreenProps {
  source: StationSource;
  action: StationAction;
  step?: StationStep;
  attemptId?: string | null;
  stationVersionId?: string | null;
  examCode: string;
  readingSeconds: number;
  simulationSeconds: number;
  index: number;
  total: number;
  attemptsUsed: number | null;
  attemptLimit: number | null;
  createAttempt: () => Promise<{ id: string }>;
  nextHref: string | null;
  completeHref: string | null;
  /** For reporting a problem — library station id when known. */
  flagStationId?: string | null;
  /** The learner's own flag, where the arm has somewhere to keep it. */
  comeBack?: ComeBackFlag | null;
}

type EndReason = "manual" | "timer" | null;

export function StationScreen(props: StationScreenProps) {
  const {
    source,
    action,
    step: initialStep,
    attemptId: attemptFromUrl,
    stationVersionId,
    readingSeconds: examReadingSeconds,
    simulationSeconds: examSimulationSeconds,
    index,
    total,
    attemptsUsed,
    attemptLimit,
    createAttempt,
    nextHref,
    completeHref,
    flagStationId,
    comeBack,
  } = props;

  const router = useRouter();
  const { hrefFor } = useSurface();
  const { replace: replaceUrl } = useStationUrl();
  const pendingFeedback = useOptionalPendingFeedback();

  /*
   * A person's own timers replace the exam's while their extra-time
   * arrangement is on. This screen is practice only, so no circuit's clock is
   * ever stretched; with no arrangement both are exactly the exam's defaults.
   */
  const { readingSeconds: effectiveReadingSeconds, simulationSeconds } = usePracticeTimers({
    readingSeconds: examReadingSeconds,
    simulationSeconds: examSimulationSeconds,
  });

  const [step, setStep] = useState<StationStep>(initialStep ?? "patient");
  const [confirmingStart, setConfirmingStart] = useState(false);
  const [readingUp, setReadingUp] = useState(false);
  const [marking, setMarking] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [isLeavingRoom, setIsLeavingRoom] = useState(false);
  const [simulationTimeUp, setSimulationTimeUp] = useState(false);
  const [completeSessionConfirm, setCompleteSessionConfirm] = useState(false);
  const [isCompletingSession, setIsCompletingSession] = useState(false);
  const [hasFeedbackReady, setHasFeedbackReady] = useState(false);
  const [finishedAttemptId, setFinishedAttemptId] = useState<string | null>(null);

  const pendingHref = useRef<string | null>(null);
  const endReasonRef = useRef<EndReason>(null);
  const hasConsultedRef = useRef(false);
  const timeUpHandledRef = useRef(false);
  const pendingKeyRef = useRef<string | null>(null);

  const stationKey =
    source.kind === "set"
      ? `${source.setId}:${source.entryId}`
      : source.kind === "practice"
        ? `practice:${source.stationId}`
        : `self:${source.orgSlug}:${source.stationId}`;

  const attempt = useStationAttempt({
    key: stationKey,
    action: finishedAttemptId ? "review" : action,
    create: createAttempt,
    attemptIdFromUrl: finishedAttemptId ?? attemptFromUrl,
    stationVersionId,
    setEntryId: source.kind === "set" ? source.entryId : null,
  });

  const registerBackgroundMarking = useCallback(() => {
    if (!pendingFeedback || !hasConsultedRef.current || !attempt.attemptId) return;
    const reviewHref =
      source.kind === "set"
        ? hrefFor(feedbackReviewHref(source.setId, source.entryId, attempt.attemptId))
        : source.kind === "practice"
          ? hrefFor(
              `/stations/${source.stationId}/practise?action=review&tab=feedback&attempt=${attempt.attemptId}`,
            )
          : hrefFor(`/attempts/${attempt.attemptId}`);

    const key = `${stationKey}:${attempt.attemptId}`;
    pendingKeyRef.current = key;
    pendingFeedback.register({
      key,
      attemptId: attempt.attemptId,
      stationLabel: total > 1 ? `Station ${index + 1}` : "Station",
      reviewHref,
    });
    pendingFeedback.release(key);
  }, [pendingFeedback, attempt.attemptId, source, hrefFor, stationKey, index, total]);

  const handleSessionEnded = useCallback(() => {
    forgetStationAttempt(stationKey);
    const reason = endReasonRef.current;
    endReasonRef.current = null;
    const isLast = nextHref === null;

    if (reason === "timer") {
      if (!isLast) {
        registerBackgroundMarking();
        setSimulationTimeUp(true);
        return;
      }
      if (!hasConsultedRef.current) {
        if (completeHref) router.push(completeHref);
        return;
      }
      setMarking(true);
      return;
    }

    setMarking(true);
  }, [nextHref, completeHref, router, stationKey, registerBackgroundMarking]);

  const session = useAttemptSession({
    attemptId: attempt.attemptId,
    readingSeconds: 0,
    onEnded: handleSessionEnded,
  });

  const effectiveAction = attempt.exhausted || finishedAttemptId ? "review" : action;
  const steps = stepsFor(effectiveAction);
  const live = session.phase === "connecting" || session.phase === "live";

  useEffect(() => {
    if (session.phase === "live") hasConsultedRef.current = true;
  }, [session.phase]);

  useEffect(() => {
    if (!attempt.attemptId || effectiveAction !== "review") return;
    let live = true;
    void readResults(attempt.attemptId).then((results) => {
      if (live) setHasFeedbackReady(results.length > 0);
    }).catch(() => {
      if (live) setHasFeedbackReady(false);
    });
    return () => {
      live = false;
    };
  }, [attempt.attemptId, effectiveAction, attempt.review]);

  const setStepAndUrl = useCallback(
    (next: StationStep) => {
      setStep(next);
      replaceUrl({ step: next, action: effectiveAction, attemptId: attempt.attemptId });
    },
    [replaceUrl, effectiveAction, attempt.attemptId],
  );

  const enterConsultation = useCallback(() => {
    setStepAndUrl("simulation");
    setConfirmingStart(false);
    setReadingUp(false);
  }, [setStepAndUrl]);

  const handleTabChange = useCallback(
    (next: StationStep) => {
      if (next === "simulation" && effectiveAction === "attempt" && step === "patient") {
        setConfirmingStart(true);
        return;
      }
      setStepAndUrl(next);
    },
    [effectiveAction, step, setStepAndUrl],
  );

  const endActiveConsultation = useCallback(async () => {
    // Moving on while in line gives the place up for whoever is behind.
    if (session.phase === "queued") await session.leaveQueue();
    if (live) {
      endReasonRef.current = "manual";
      await session.end();
    }
  }, [live, session]);

  const handleSimulationTimeUp = useCallback(async () => {
    if (timeUpHandledRef.current) return;
    timeUpHandledRef.current = true;
    endReasonRef.current = "timer";
    if (live) await session.end();
    else handleSessionEnded();
  }, [live, session, handleSessionEnded]);

  const handleNextStation = useCallback(async () => {
    await endActiveConsultation();
    if (effectiveAction === "attempt") registerBackgroundMarking();
    if (nextHref) router.push(nextHref);
  }, [endActiveConsultation, effectiveAction, registerBackgroundMarking, nextHref, router]);

  const finishWithoutFeedback = useCallback(() => {
    pendingFeedback?.pushNotice({
      tone: "info",
      title: `No consultation recorded for Station ${index + 1}`,
      message:
        "The simulation wasn't started, so there is nothing to mark. You can attempt the station again from the station page.",
    });
    if (completeHref) router.push(completeHref);
  }, [pendingFeedback, index, completeHref, router]);

  const executeCompletionProcess = useCallback(() => {
    registerBackgroundMarking();
    setMarking(true);
  }, [registerBackgroundMarking]);

  const handleCompleteSessionIntent = useCallback(() => {
    setCompleteSessionConfirm(true);
  }, []);

  const confirmCompleteSession = useCallback(async () => {
    if (isCompletingSession) return;
    setIsCompletingSession(true);
    setCompleteSessionConfirm(false);
    setReadingUp(false);
    if (!hasConsultedRef.current) {
      finishWithoutFeedback();
      setIsCompletingSession(false);
      return;
    }
    await endActiveConsultation();
    executeCompletionProcess();
    setIsCompletingSession(false);
  }, [
    isCompletingSession,
    finishWithoutFeedback,
    endActiveConsultation,
    executeCompletionProcess,
  ]);

  const leaveTo = useCallback(
    (href: string) => {
      if (live) {
        pendingHref.current = href;
        setLeaving(true);
        return;
      }
      router.push(href);
    },
    [live, router],
  );

  useEffect(() => {
    if (!live) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    const interceptLink = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const target = event.target instanceof Element ? event.target : null;
      const anchor = target?.closest<HTMLAnchorElement>("a[href]");
      if (!anchor || anchor.target === "_blank" || anchor.hasAttribute("download")) return;
      const url = new URL(anchor.href, window.location.href);
      if (url.origin !== window.location.origin || url.href === window.location.href) return;
      event.preventDefault();
      event.stopPropagation();
      pendingHref.current = url.pathname + url.search + url.hash;
      setLeaving(true);
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", interceptLink, true);
    return () => {
      window.removeEventListener("beforeunload", warn);
      document.removeEventListener("click", interceptLink, true);
    };
  }, [live]);

  if (attempt.loading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner />
      </div>
    );
  }

  if (attempt.error) {
    return <Alert tone="danger">{errorMessage(attempt.error)}</Alert>;
  }

  const activeStep = steps.includes(step) ? step : steps[0]!;
  const isLast = nextHref === null;
  const onReading = activeStep === "patient" && effectiveAction === "attempt";
  const demoteStationNav = onReading || activeStep === "feedback";

  return (
    <div className="flex flex-col">
      <StationHeader
        index={index}
        total={total}
        attemptsUsed={attemptsUsed}
        attemptLimit={attemptLimit}
        flagStationId={flagStationId}
        comeBack={comeBack}
      />

      <div className="flex flex-col items-center justify-between lg:flex-row">
        <StationTabs
          steps={steps}
          active={activeStep}
          onChange={handleTabChange}
          feedbackReady={hasFeedbackReady}
        />

        {effectiveAction === "attempt" && attempt.attemptId && (
          <div className="mt-4 lg:mt-0">
            {step === "patient" && (
              <Timer
                duration={effectiveReadingSeconds}
                stationId={attempt.attemptId}
                timerType="doctor"
                onTimeUp={enterConsultation}
              />
            )}
            {activeStep === "simulation" && (
              <Timer
                duration={simulationSeconds}
                stationId={attempt.attemptId}
                timerType="simulation"
                running={session.patientJoined}
                onTimeUp={() => void handleSimulationTimeUp()}
                onFinalCountdown={session.warnTimeRemaining}
              />
            )}
          </div>
        )}
      </div>

      <div className="mb-4 mt-8 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-3 lg:mt-6">
        <Button
          type="button"
          variant={demoteStationNav ? "secondary" : "primary"}
          onClick={() =>
            isLast
              ? handleCompleteSessionIntent()
              : onReading
                ? leaveTo(nextHref!)
                : handleNextStation()
          }
          disabled={live}
          className={cn(
            "w-full gap-2 sm:w-auto",
            isLast && (effectiveAction === "review" || activeStep === "feedback") && "hidden",
          )}
        >
          {isLast ? (
            <>
              <HiOutlineCheckCircle className="h-4 w-4" aria-hidden />
              <span>{onReading ? "Skip to complete session" : "Complete session"}</span>
            </>
          ) : (
            <>
              <HiOutlineArrowRight className="h-4 w-4" aria-hidden />
              <span>{onReading ? "Skip to next station" : "Next station"}</span>
            </>
          )}
        </Button>

        {onReading && (
          <Button
            type="button"
            onClick={() => setConfirmingStart(true)}
            className="w-full gap-2 sm:w-auto"
          >
            <HiOutlineMicrophone className="h-4 w-4" aria-hidden />
            <span>Start simulation</span>
          </Button>
        )}
      </div>

      {onReading && (
        <p className="-mt-2 mb-4 text-osce-meta text-b2c-text-muted sm:text-right">
          Read the brief, then start the simulation. If reading time runs out, it starts on its
          own.
        </p>
      )}

      <div className="mt-4">
        {activeStep === "patient" &&
          (attempt.brief ? (
            <StationBrief brief={attempt.brief} />
          ) : (
            <Alert tone="info">There is no written brief for this station.</Alert>
          ))}

        {(activeStep === "simulation" || live) && (
          <div hidden={activeStep !== "simulation"}>
          <ConsultationScreen
            coverage={effectiveAction === "attempt" ? <LiveCoveragePanel attemptId={attempt.attemptId} isLive={session.phase === "live"} /> : undefined}
            sticky={effectiveAction === "attempt"}
            showTerms={effectiveAction === "attempt"}
            asideTitle={effectiveAction === "attempt" ? "Doctor information" : "Transcription"}
            asideIcon={effectiveAction === "attempt" ? HiOutlineIdentification : HiOutlineDocumentText}
            asideTone={effectiveAction === "attempt" ? "primary" : "sky"}
            panel={
              <ConsultationPanel
                session={session}
                durationSeconds={simulationSeconds}
                patient={consultationPatientFromBrief(attempt.brief)}
                disabledReason={
                  attempt.exhausted
                    ? "You have used every attempt at this station."
                    : effectiveAction === "review"
                      ? "This consultation is over. Start a new attempt to speak to the patient again."
                      : null
                }
              />
            }
            aside={
              effectiveAction === "attempt" ? (
                attempt.brief ? (
                  <StationBrief brief={attempt.brief} embedded />
                ) : null
              ) : (
                <TranscriptStep
                  attemptId={attempt.attemptId}
                  stationVersionId={stationVersionId ?? attempt.brief?.station_version_id ?? null}
                />
              )
            }
          />
          </div>
        )}

        {activeStep === "management" &&
          (attempt.review ? (
            <ManagementPlanView review={attempt.review} />
          ) : (
            <Alert tone="info">
              The model answer appears here once the consultation is finished.
            </Alert>
          ))}

        {activeStep === "feedback" && (
          <FeedbackStep
            attemptId={attempt.attemptId}
            examCode={props.examCode}
            setId={source.kind === "set" ? source.setId : null}
            entryId={source.kind === "set" ? source.entryId : null}
            stationVersionId={stationVersionId ?? attempt.brief?.station_version_id ?? null}
            brief={attempt.brief}
            review={attempt.review}
          />
        )}
      </div>

      <ConfirmModal
        isOpen={confirmingStart}
        onCancel={() => {
          setConfirmingStart(false);
        }}
        onConfirm={enterConsultation}
        closeOnBack={false}
        message="Start the consultation now? Reading time ends now, and the consultation timer starts when the patient joins."
      />

      <ConfirmModal
        isOpen={readingUp && !marking && !completeSessionConfirm}
        onCancel={() => setReadingUp(false)}
        onConfirm={enterConsultation}
        message="Reading time is up. Moving you on to the consultation."
        cancelButton={false}
      />

      <ConfirmModal
        title="End session"
        isOpen={completeSessionConfirm}
        onCancel={() => setCompleteSessionConfirm(false)}
        onConfirm={() => void confirmCompleteSession()}
        message="This ends the session and starts marking your consultation. If you haven't started the simulation yet, cancel and press Start simulation first."
      />

      <SimulationTimeUpModal
        isOpen={simulationTimeUp}
        isLastStation={isLast}
        onNext={() => {
          setSimulationTimeUp(false);
          if (isLast && completeHref) router.push(completeHref);
          else if (nextHref) router.push(nextHref);
        }}
      />

      <MarkingModal
        isOpen={marking}
        attemptId={attempt.attemptId}
        examCode={props.examCode}
        onReady={() => {
          setMarking(false);
          setFinishedAttemptId(attempt.attemptId);
          setHasFeedbackReady(true);
          setStep("feedback");
          replaceUrl({ step: "feedback", action: "review", attemptId: attempt.attemptId });
          if (pendingKeyRef.current) pendingFeedback?.resolve(pendingKeyRef.current);
        }}
        onSkip={() => {
          setMarking(false);
          if (pendingKeyRef.current) pendingFeedback?.release(pendingKeyRef.current);
          if (completeHref) router.push(completeHref);
        }}
      />

      <LeaveConfirmModal
        isOpen={leaving}
        title="Leave this consultation?"
        message="The station will end now and you'll get feedback on what you've said so far. You can't resume it."
        leaveText="End and leave"
        stayText="Stay"
        isLeaving={isLeavingRoom}
        onStay={() => {
          pendingHref.current = null;
          setLeaving(false);
        }}
        onLeave={() => {
          const href = pendingHref.current;
          setLeaving(false);
          setIsLeavingRoom(true);
          endReasonRef.current = "manual";
          void session.end().then(() => {
            setIsLeavingRoom(false);
            if (effectiveAction === "attempt") registerBackgroundMarking();
            if (href) router.push(href);
          });
        }}
      />
    </div>
  );
}

export { STEP_LABELS };
