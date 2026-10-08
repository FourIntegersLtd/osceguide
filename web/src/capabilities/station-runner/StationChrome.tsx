"use client";

import { useState, type ReactNode } from "react";
import { HiOutlineCheck } from "react-icons/hi2";
import { LuFlag, LuMessageSquareWarning } from "react-icons/lu";
import { Back, cn, productTokens, Spinner } from "@/foundation/ui";
import { useToast } from "@/foundation/hooks";
import { flagStation } from "@/capabilities/stations/api";
import { actionFailureText } from "./actionFailure";
import type { StationAction } from "@/capabilities/station-runner/useStationAttempt";

export type StationStep = "patient" | "simulation" | "management" | "feedback";

/** The learner's own "come back to" flag on this station, and how to change it. */
export interface ComeBackFlag {
  initial: boolean;
  save: (flagged: boolean) => Promise<void>;
}

/** The four steps, numbered as the retiring client numbered them. */
export const STEP_LABELS: Record<StationStep, string> = {
  patient: "Reading time",
  simulation: "Consultation",
  management: "Management",
  feedback: "Feedback",
};

const STEP_NUMBER: Record<StationStep, string> = {
  patient: "1",
  simulation: "2",
  management: "3",
  feedback: "4",
};

/** Which steps exist. Sitting a station is only steps one and two. */
export function stepsFor(action: StationAction): StationStep[] {
  return action === "review"
    ? ["patient", "simulation", "management", "feedback"]
    : ["patient", "simulation"];
}

/**
 * Where you are in the session, and how many goes you have left.
 *
 * "Station 3 of 8" rather than the station's name, which is the retiring
 * client's and is deliberate: the name gives away the case before it is sat.
 */
export function StationHeader({
  index,
  total,
  attemptsUsed,
  attemptLimit,
  flagStationId,
  comeBack,
  backHref,
  aside,
}: {
  index: number;
  total: number;
  attemptsUsed: number | null;
  attemptLimit: number | null;
  flagStationId?: string | null;
  /**
   * Flagging this station to come back to: the learner's own list, the
   * Flagged tab. The arm supplies it where there is somewhere to keep the
   * flag (a practice set's entry); without it only reporting is offered.
   */
  comeBack?: ComeBackFlag | null;
  /** A link for Back (the session page) instead of the browser history. */
  backHref?: string;
  /** The clock and the step's one action, at the header's right (canvas `train-reading`). */
  aside?: ReactNode;
}) {
  const toast = useToast();
  const [flagged, setFlagged] = useState(false);
  const [marked, setMarked] = useState(comeBack?.initial ?? false);
  const [marking, setMarking] = useState(false);
  const [reporting, setReporting] = useState(false);

  const onMark = async () => {
    if (!comeBack || marking) return;
    const next = !marked;
    setMarking(true);
    try {
      await comeBack.save(next);
      setMarked(next);
      toast.show({
        tone: "success",
        title: next ? "Flagged to come back to" : "Flag removed",
        message: next ? "Find it under Flagged stations." : "It is off your Flagged stations.",
      });
    } catch (cause) {
      toast.show({
        tone: "error",
        title: "We couldn't change the flag",
        message: actionFailureText(cause),
      });
    } finally {
      setMarking(false);
    }
  };
  const completed =
    attemptsUsed !== null && attemptLimit !== null && attemptsUsed >= attemptLimit;

  const onFlag = async () => {
    if (!flagStationId || reporting) return;
    setReporting(true);
    try {
      await flagStation(flagStationId);
      setFlagged(true);
      toast.show({
        tone: "success",
        title: "Problem reported",
        message: "Thanks. Our team will take a look at this station.",
      });
    } catch (cause) {
      toast.show({
        tone: "error",
        title: "We couldn't report this station",
        message: actionFailureText(cause),
      });
    } finally {
      setReporting(false);
    }
  };

  return (
    <div className="mb-5 flex flex-col gap-3">
      <Back href={backHref} />
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className={productTokens.b2cPageTitle}>
            {total > 1 ? `Station ${index + 1} of ${total}` : "Station"}
          </h1>
          {attemptsUsed !== null && attemptLimit !== null && (
            <span
              className={cn(
                "inline-flex h-[22px] items-center rounded-[6px] px-2 text-osce-meta font-medium",
                completed
                  ? "bg-osce-success-bg text-osce-success-text"
                  : "bg-b2c-surface-muted text-b2c-text-secondary",
              )}
            >
              {completed ? "Completed" : `Attempts: ${attemptsUsed}/${attemptLimit}`}
            </span>
          )}
          {comeBack ? (
            <button
              type="button"
              onClick={() => void onMark()}
              disabled={marking}
              aria-busy={marking || undefined}
              aria-pressed={marked}
              aria-label="Flag this station to come back to"
              title={marked ? "Flagged to come back to" : "Flag this station to come back to"}
              className={productTokens.b2cIconButton}
            >
              {marking ? (
                <Spinner label="Saving flag" />
              ) : (
                <LuFlag
                  aria-hidden
                  className={cn("h-4 w-4", marked && "fill-current text-osce-accent")}
                />
              )}
            </button>
          ) : null}
          {flagStationId ? (
            <button
              type="button"
              onClick={() => void onFlag()}
              disabled={reporting}
              aria-busy={reporting || undefined}
              aria-pressed={flagged}
              aria-label="Report a problem with this station"
              title="Report a problem with this station"
              className={productTokens.b2cIconButton}
            >
              {reporting ? (
                <Spinner label="Reporting" />
              ) : (
                <LuMessageSquareWarning
                  aria-hidden
                  className={cn("h-4 w-4", flagged && "text-osce-danger")}
                />
              )}
            </button>
          ) : null}
        </div>
        {aside ? (
          <div className="flex flex-wrap items-end gap-x-5 gap-y-3 sm:justify-end">{aside}</div>
        ) : null}
      </div>
    </div>
  );
}

/**
 * The steps as one numbered row (canvas `train-reading`, `train-management`).
 * It scrolls sideways on a phone rather than turning into a select, so the
 * step you are on is always visible.
 */
export function StationTabs({
  steps,
  active,
  onChange,
  feedbackReady = false,
}: {
  steps: StationStep[];
  active: StationStep;
  onChange: (step: StationStep) => void;
  feedbackReady?: boolean;
}) {
  const activeIndex = steps.indexOf(active);
  return (
    <nav aria-label="Station steps" className="-mx-1 overflow-x-auto">
      <ol className="flex min-w-max items-center gap-1 border-b border-osce-border-light px-1">
        {steps.map((step, position) => {
          const isActive = step === active;
          const isDone = position < activeIndex;
          return (
            <li key={step}>
              <button
                type="button"
                onClick={() => onChange(step)}
                aria-current={isActive ? "step" : undefined}
                className={cn(
                  "-mb-px flex h-11 items-center gap-2 border-b-2 px-3 text-osce-body font-medium transition-colors",
                  isActive
                    ? "border-osce-ink-900 text-osce-ink-900"
                    : "border-transparent text-b2c-text-muted hover:text-osce-ink-900",
                )}
              >
                <span
                  className={cn(
                    "flex h-5 w-5 items-center justify-center rounded-full font-mono text-osce-micro tabular-nums",
                    isActive
                      ? "bg-osce-accent text-white"
                      : "bg-b2c-surface-muted text-b2c-text-secondary",
                  )}
                >
                  {isDone ? <HiOutlineCheck className="h-3 w-3" aria-hidden /> : STEP_NUMBER[step]}
                </span>
                {STEP_LABELS[step]}
                {step === "feedback" && feedbackReady ? (
                  <span className="h-1.5 w-1.5 rounded-full bg-osce-success-icon" aria-label="Ready" />
                ) : null}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
