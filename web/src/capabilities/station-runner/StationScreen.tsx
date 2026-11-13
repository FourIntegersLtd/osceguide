"use client";
import { LiveCoveragePanel } from "@/capabilities/attempt-runner/coverage/LiveCoveragePanel";
import { NonverbalCuesPanel } from "@/capabilities/attempt-runner/nonverbal/NonverbalCuesPanel";
import { useNonverbal } from "@/capabilities/attempt-runner/nonverbal/useNonverbal";
import { consultationClock } from "@/capabilities/attempt-runner/consultation/consultationClock";

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
  Spinner,
  Timer,
  cn,
} from "@/foundation/ui";
import { b2cRoomFill, b2cRoomOverlay } from "@/foundation/ui/productTokens";
import { useSurface } from "@/capabilities";
import { StartFailureAlert } from "@/capabilities/station-runner/StartFailureAlert";
import { phaseElapsedSeconds } from "@/capabilities/station-runner/stationClock";
import { StartGate } from "@/capabilities/station-runner/StartGate";
import { endOutcome, type EndReason } from "@/capabilities/station-runner/sessionEnd";
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
import { useOptionalPendingFeedback } from "@/capabilities/pending-feedback";
import { useLeaveGuard } from "@/foundation/hooks";
import {
  feedbackPathFor,
  stationKeyFor,
  type StationSource,
} from "@/capabilities/station-runner/stationSource";

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
  /** Where Back goes. Without it Back steps through the browser history. */
  backHref?: string;
  nextHref: string | null;
  completeHref: string | null;
  /** For reporting a problem — library station id when known. */
  flagStationId?: string | null;
  /** The learner's own flag, where the arm has somewhere to keep it. */
  comeBack?: ComeBackFlag | null;
}

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
    backHref,
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
  const [marking, setMarking] = useState(false);
  const [isLeavingRoom, setIsLeavingRoom] = useState(false);
  const [simulationTimeUp, setSimulationTimeUp] = useState(false);
  const [completeSessionConfirm, setCompleteSessionConfirm] = useState(false);
  const [isCompletingSession, setIsCompletingSession] = useState(false);
  const [hasFeedbackReady, setHasFeedbackReady] = useState(false);
  const [finishedAttemptId, setFinishedAttemptId] = useState<string | null>(null);

  const endReasonRef = useRef<EndReason>(null);
  const hasConsultedRef = useRef(false);
  const timeUpHandledRef = useRef(false);
  const pendingKeyRef = useRef<string | null>(null);

  const stationKey = stationKeyFor(source);

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
    const reviewHref = hrefFor(feedbackPathFor(source, attempt.attemptId));
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
    const outcome = endOutcome({
      reason,
      isLast: nextHref === null,
      consulted: hasConsultedRef.current,
    });

    switch (outcome) {
      case "time-up":
        registerBackgroundMarking();
        setSimulationTimeUp(true);
        break;
      case "next":
        registerBackgroundMarking();
        if (nextHref) router.push(nextHref);
        break;
      case "summary":
        if (completeHref) router.push(completeHref);
        break;
      case "mark":
        setMarking(true);
        break;
      case "none": // the button that ended it navigates itself
        break;
      default: {
        const unhandled: never = outcome;
        return unhandled;
      }
    }
  }, [nextHref, completeHref, router, stationKey, registerBackgroundMarking]);

  const session = useAttemptSession({
    attemptId: attempt.attemptId,
    readingSeconds: 0,
    onEnded: handleSessionEnded,
  });

  const effectiveAction = attempt.exhausted || finishedAttemptId ? "review" : action;
  const nonverbal = useNonverbal(effectiveAction === "attempt" ? attempt.attemptId : null, session.phase === "live");
  const steps = stepsFor(effectiveAction);
  const live = session.phase === "connecting" || session.phase === "live";
  const leaveGuard = useLeaveGuard(live);

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
  }, [setStepAndUrl]);

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

  if (attempt.loading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner size="md" />
      </div>
    );
  }

  const leaveHref = backHref ?? completeHref;
  const goBack = () => (leaveHref ? router.push(leaveHref) : router.back());
  if (attempt.error) {
    return <StartFailureAlert cause={attempt.error} onRetry={attempt.reload} onBack={goBack} />;
  }

  if (attempt.gate) {
    return (
      <StartGate
        gate={attempt.gate}
        readingSeconds={effectiveReadingSeconds}
        simulationSeconds={simulationSeconds}
        onStart={attempt.start}
        onStartAgain={attempt.startAgain}
        onBack={goBack}
      />
    );
  }

  const activeStep = steps.includes(step) ? step : steps[0]!;
  const isLast = nextHref === null;
  const onReading = activeStep === "patient" && effectiveAction === "attempt";
  const demoteStationNav = onReading || activeStep === "feedback";

  // The live consultation fills the content column; only its stage card takes
  // the room skin (ConsultationScreen), the rest stays on the page's surface.
  const inRoom = effectiveAction === "attempt" && activeStep === "simulation";
  const timer =
    effectiveAction === "attempt" && attempt.attemptId && attempt.briefReceivedAt !== null ? (
      step === "patient" ? (
        <Timer
          duration={effectiveReadingSeconds}
          stationId={attempt.attemptId}
          timerType="doctor"
          elapsedSeconds={phaseElapsedSeconds(attempt.brief, "reading")}
          measuredAtMs={attempt.briefReceivedAt}
          onTimeUp={enterConsultation}
        />
      ) : activeStep === "simulation" ? (
        <Timer
          duration={simulationSeconds}
          stationId={attempt.attemptId}
          timerType="simulation"
          elapsedSeconds={phaseElapsedSeconds(attempt.brief, "consultation")}
          measuredAtMs={attempt.briefReceivedAt}
          {...consultationClock(session.phase, session.patientJoined)}
          onTimeUp={() => void handleSimulationTimeUp()}
          onFinalCountdown={session.warnTimeRemaining}
        />
      ) : null
    ) : null;
  const hideStationNav =
    isLast && (effectiveAction === "review" || activeStep === "feedback");

  // Shared by the header (live, review) and the reading row.
  const stationNav = hideStationNav ? null : (
    <Button
      type="button"
      variant={demoteStationNav ? "secondary" : "primary"}
      onClick={() =>
        isLast
          ? handleCompleteSessionIntent()
          : onReading
            ? leaveGuard.leaveTo(nextHref!)
            : handleNextStation()
      }
      disabled={live}
      className="gap-2"
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
  );

  return (
    <div
      className={cn(
        // The live room fills the content column, toolbar included.
        inRoom ? cn(b2cRoomOverlay, "px-3 pt-3 sm:px-4 sm:pt-4 md:pb-4") : "flex flex-col",
      )}
    >
      <StationHeader
        index={index}
        total={total}
        attemptsUsed={attemptsUsed}
        attemptLimit={attemptLimit}
        flagStationId={flagStationId}
        comeBack={comeBack}
        backHref={backHref}
        aside={
          onReading ? null : (
            <>
              {timer}
              {stationNav}
            </>
          )
        }
      />

      {onReading && (
        <>
          {/* One row: start on the left, the clock and the skip on the right; it wraps on a phone. */}
          <div className="flex flex-wrap items-center justify-between gap-x-5 gap-y-3">
            <Button type="button" onClick={() => setConfirmingStart(true)} className="gap-2">
              <HiOutlineMicrophone className="h-4 w-4" aria-hidden />
              <span>Start simulation</span>
            </Button>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
              {timer}
              {stationNav}
            </div>
          </div>
          <p className="mt-3 text-osce-meta text-b2c-text-muted">
            Read the brief, then start the simulation. If reading time runs out, it starts on its
            own.
          </p>
        </>
      )}

      {effectiveAction === "review" && (
        <StationTabs
          steps={steps}
          active={activeStep}
          onChange={setStepAndUrl}
          feedbackReady={hasFeedbackReady}
        />
      )}

      <div className={cn("mt-5", inRoom && b2cRoomFill)}>
        {activeStep === "patient" &&
          (attempt.brief ? (
            <StationBrief brief={attempt.brief} />
          ) : (
            <Alert tone="info">There is no written brief for this station.</Alert>
          ))}

        {(activeStep === "simulation" || live) && (
          <div hidden={activeStep !== "simulation"} className={cn(inRoom && b2cRoomFill)}>
          <ConsultationScreen
            fill={inRoom}
            coverage={effectiveAction === "attempt" ? <LiveCoveragePanel attemptId={attempt.attemptId} isLive={session.phase === "live"} patientJoined={session.patientJoined} /> : undefined}
            cues={effectiveAction === "attempt" && nonverbal.read?.supported ? {
              panel: <NonverbalCuesPanel nonverbal={nonverbal} isLive={session.phase === "live"} />,
              alert: nonverbal.live.tone === "warning",
              defaultTab: nonverbal.read.consented && !nonverbal.off ? "cues" : "covered",
              cameraOn: nonverbal.capture.status === "starting" || nonverbal.capture.status === "running",
              onTurnOff: nonverbal.turnOff,
            } : undefined}
            sticky={effectiveAction === "attempt"}
            showTerms={effectiveAction === "attempt"}
            asideTitle={effectiveAction === "attempt" ? "Doctor information" : "Transcription"}
            asideIcon={effectiveAction === "attempt" ? HiOutlineIdentification : HiOutlineDocumentText}
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
        title="End session"
        isOpen={completeSessionConfirm}
        onCancel={() => setCompleteSessionConfirm(false)}
        onConfirm={() => confirmCompleteSession()}
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
        isOpen={leaveGuard.asking}
        title="Leave this consultation?"
        message="The station will end now and you'll get feedback on what you've said so far. You can't resume it."
        leaveText="End and leave"
        stayText="Stay"
        isLeaving={isLeavingRoom}
        onStay={leaveGuard.stay}
        onLeave={() => {
          const href = leaveGuard.confirmLeave();
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
