"use client";

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
  useAttemptSession,
} from "@/capabilities/attempt-runner";
import { MarkingModal } from "@/domains/train/station/MarkingModal";
import { FeedbackStep } from "@/domains/train/station/FeedbackStep";
import { TranscriptStep } from "@/domains/train/station/TranscriptStep";
import {
  STEP_LABELS,
  StationHeader,
  StationTabs,
  stepsFor,
  type StationStep,
} from "@/domains/train/station/StationChrome";
import {
  forgetStationAttempt,
  useStationAttempt,
  type StationAction,
} from "@/domains/train/station/useStationAttempt";

export interface StationScreenProps {
  /** Identifies the station being sat, and how to start it. */
  source:
    | { kind: "set"; setId: string; entryId: string }
    | { kind: "practice"; stationId: string };
  action: StationAction;
  step?: StationStep;
  /** A particular past attempt to review, rather than the most recent. */
  attemptId?: string | null;
  stationVersionId?: string | null;
  examCode: string;
  readingSeconds: number;
  simulationSeconds: number;
  index: number;
  total: number;
  attemptsUsed: number | null;
  attemptLimit: number | null;
  /** Start this station's attempt. Called once, when the screen opens. */
  createAttempt: () => Promise<{ id: string }>;
  /** Where "Next station" goes, or null on the last one. */
  nextHref: string | null;
  /** Where "Complete session" goes. */
  completeHref: string | null;
}

/**
 * One station, from the brief to the feedback.
 *
 * The retiring client's `NewStationDetail`, which is one screen with four
 * numbered steps: read the notes, talk to the patient, then — once it is
 * over — compare against the model answer and read the marking. The platform
 * had none of that: a generic runner with no brief at all (nothing served one),
 * no management step, and feedback on a separate page somebody had to be
 * navigated to.
 *
 * What is genuinely different here is that the attempt is created when the
 * screen opens rather than when the patient is called, because the brief is
 * read *off the attempt* — that is what makes it the candidate's to see.
 * `useStationAttempt` keeps the id across a reload so a refresh does not spend
 * a second go.
 */
export function StationScreen(props: StationScreenProps) {
  const {
    source,
    action,
    step: initialStep,
    attemptId: attemptFromUrl,
    stationVersionId,
    readingSeconds,
    simulationSeconds,
    index,
    total,
    attemptsUsed,
    attemptLimit,
    createAttempt,
    nextHref,
    completeHref,
  } = props;

  const router = useRouter();
  const { hrefFor } = useSurface();

  const [step, setStep] = useState<StationStep>(initialStep ?? "patient");
  const [confirmingStart, setConfirmingStart] = useState(false);
  const [readingUp, setReadingUp] = useState(false);
  const [marking, setMarking] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const pendingHref = useRef<string | null>(null);

  const stationKey =
    source.kind === "set" ? `${source.setId}:${source.entryId}` : `practice:${source.stationId}`;

  const attempt = useStationAttempt({
    key: stationKey,
    action,
    create: createAttempt,
    attemptIdFromUrl: attemptFromUrl,
    stationVersionId,
    setEntryId: source.kind === "set" ? source.entryId : null,
  });

  const session = useAttemptSession({
    attemptId: attempt.attemptId,
    readingSeconds: 0, // The step tabs are the reading period, not the hook's.
    onEnded: () => {
      forgetStationAttempt(stationKey);
      setMarking(true);
    },
  });

  // Nothing left to sit means there is nothing to sit *now*: the station reads
  // back like a review, which is what the retiring client's "Completed" pill
  // meant. Refusing the screen outright would hide a station somebody has
  // already paid for and sat.
  const effectiveAction = attempt.exhausted ? "review" : action;
  const steps = stepsFor(effectiveAction);
  const live = session.phase === "connecting" || session.phase === "live";

  // Moving to the consultation step is what calls the patient. The old client
  // had the same coupling and it is the right one: a candidate who has clicked
  // through to step two has said they are ready.
  const enterConsultation = useCallback(() => {
    setStep("simulation");
    setConfirmingStart(false);
    setReadingUp(false);
    if (effectiveAction === "attempt" && session.phase === "idle") void session.startConsultation();
  }, [effectiveAction, session]);

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

  // A consultation in progress must survive a stray click on "Next station",
  // and must not survive the browser being closed silently.
  useEffect(() => {
    if (!live) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
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

  // A tab from the URL that this action does not offer — `management` on a
  // station being sat — falls back rather than rendering nothing.
  const activeStep = steps.includes(step) ? step : steps[0]!;
  const isLast = nextHref === null;
  const onReading = activeStep === "patient" && effectiveAction === "attempt";

  return (
    <div className="flex flex-col">
      <StationHeader
        index={index}
        total={total}
        attemptsUsed={attemptsUsed}
        attemptLimit={attemptLimit}
      />

      <div className="flex flex-col items-center justify-between lg:flex-row">
        <StationTabs steps={steps} active={activeStep} onChange={setStep} />

        {effectiveAction === "attempt" && attempt.attemptId && (
          <div className="mt-4 lg:mt-0">
            {step === "patient" && (
              <Timer
                duration={readingSeconds}
                stationId={attempt.attemptId}
                timerType="doctor"
                onTimeUp={() => setReadingUp(true)}
              />
            )}
            {activeStep === "simulation" && (
              <Timer
                duration={simulationSeconds}
                stationId={attempt.attemptId}
                timerType="simulation"
                onTimeUp={() => void session.end()}
                onFinalCountdown={session.warnTimeRemaining}
              />
            )}
          </div>
        )}
      </div>

      <div className="mb-4 mt-8 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-3 lg:mt-6">
        <Button
          type="button"
          variant={onReading ? "secondary" : "primary"}
          onClick={() => leaveTo(isLast ? (completeHref ?? hrefFor("/mocks")) : nextHref!)}
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

        {activeStep === "simulation" && (
          <ConsultationScreen
            sticky={effectiveAction === "attempt"}
            showTerms={effectiveAction === "attempt"}
            asideTitle={effectiveAction === "attempt" ? "Doctor information" : "Transcription"}
            asideIcon={effectiveAction === "attempt" ? HiOutlineIdentification : HiOutlineDocumentText}
            asideTone={effectiveAction === "attempt" ? "primary" : "sky"}
            panel={
              <ConsultationPanel
                session={session}
                durationSeconds={simulationSeconds}
                patient={{
                  name: attempt.brief?.patient.name_line || "Your patient",
                  detail: attempt.brief?.station_title,
                }}
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
          />
        )}
      </div>

      <ConfirmModal
        isOpen={confirmingStart}
        onCancel={() => setConfirmingStart(false)}
        onConfirm={enterConsultation}
        closeOnBack={false}
        message="Start the consultation now? Reading time ends and the consultation timer starts immediately."
      />

      <ConfirmModal
        isOpen={readingUp && !marking}
        onCancel={() => setReadingUp(false)}
        onConfirm={enterConsultation}
        message="Reading time is up. Moving you on to the consultation."
        cancelButton={false}
      />

      <MarkingModal
        isOpen={marking}
        attemptId={attempt.attemptId}
        examCode={props.examCode}
        onReady={() => {
          setMarking(false);
          attempt.reload();
          setStep("feedback");
        }}
        onSkip={() => {
          setMarking(false);
          if (completeHref) router.push(completeHref);
        }}
      />

      <LeaveConfirmModal
        isOpen={leaving}
        title="Leave this consultation?"
        message="The consultation is still running. If you leave now it will be ended and sent for marking."
        leaveText="End and leave"
        onStay={() => {
          pendingHref.current = null;
          setLeaving(false);
        }}
        onLeave={() => {
          const href = pendingHref.current;
          setLeaving(false);
          void session.end().then(() => {
            if (href) router.push(href);
          });
        }}
      />
    </div>
  );
}

/** Exported for the step labels the route files use in their page titles. */
export { STEP_LABELS };
