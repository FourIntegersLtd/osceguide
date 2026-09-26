"use client";

import { LuStethoscope } from "react-icons/lu";
import { HiOutlineArrowRightOnRectangle, HiOutlineUser } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { phaseLabel, phaseTitle, type RunnerPhase } from "../support/sessionState";
import { formatCountdown } from "../support/examTimers";
import { ReportAbuseButton } from "./SafetyActions";

/**
 * The bar across the top of a practice session: which phase, which role, the
 * server's clock for the phase, and the way out.
 *
 * `seconds` is read from the server's `phase_ends_at`; before the clock starts
 * it is the phase's full length, as the retiring header showed it.
 */
export function SessionHeader({
  sessionId,
  role,
  phase,
  stationName,
  seconds,
  onEndSession,
}: {
  sessionId: string;
  role: "doctor" | "patient";
  phase: RunnerPhase;
  stationName: string;
  seconds: number;
  onEndSession: () => void;
}) {
  const caption = phaseLabel(phase);
  const isDoctor = role === "doctor";
  const showReportAbuse = phase === "consultation" || phase === "debrief";

  return (
    <div className="flex-shrink-0 border-b border-b2c-border bg-osce-surface">
      <div className="mx-auto max-w-7xl px-3 py-3 sm:px-4 sm:py-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center sm:gap-4">
          <div className="flex min-w-0 flex-1 items-center gap-3 sm:gap-4">
            <div className={`flex-shrink-0 rounded-lg p-2 ${isDoctor ? "bg-osce-accent-subtle" : "bg-osce-success-bg"}`}>
              {isDoctor ? (
                <LuStethoscope className="h-4 w-4 text-osce-accent sm:h-5 sm:w-5" />
              ) : (
                <HiOutlineUser className="h-4 w-4 text-osce-success-text sm:h-5 sm:w-5" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-osce-body font-semibold text-osce-ink-900">{phaseTitle(phase)}</h1>
              <p className="truncate text-osce-body text-b2c-text-secondary">
                Role:{" "}
                <span className={`font-medium capitalize ${isDoctor ? "text-osce-accent" : "text-osce-success-text"}`}>
                  {role}
                </span>
                <span className="text-b2c-text-muted"> · {caption}</span>
                {!isDoctor && <span className="hidden sm:inline">{` | Station: ${stationName}`}</span>}
              </p>
              {!isDoctor && (
                <p className="mt-1 truncate text-osce-body text-b2c-text-muted sm:hidden">Station: {stationName}</p>
              )}
            </div>
          </div>
          <div className="flex flex-shrink-0 items-center justify-between gap-2 sm:justify-end sm:gap-3">
            <div className="text-center sm:text-right">
              <div role="timer" className="font-mono text-osce-body font-bold text-osce-danger">
                {formatCountdown(seconds)}
              </div>
              <div className="text-osce-body text-b2c-text-muted">{caption}</div>
            </div>
            {showReportAbuse && <ReportAbuseButton sessionId={sessionId} className="flex-shrink-0" />}
            <Button type="button" variant="danger" size="md" onClick={onEndSession} className="shrink-0 gap-1 sm:gap-2">
              <HiOutlineArrowRightOnRectangle className="h-4 w-4" />
              <span className="hidden sm:inline">End Session</span>
              <span className="sm:hidden">End</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
