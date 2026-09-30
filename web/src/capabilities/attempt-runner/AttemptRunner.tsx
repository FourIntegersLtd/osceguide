"use client";

import { useEffect } from "react";
import Markdown from "react-markdown";
import { LuPhoneOff } from "react-icons/lu";
import { Alert, Button, Card, Spinner } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { AgentTile, VoiceRoom, useMicPreflight } from "@/foundation/livekit";
import { ExamClock } from "@/capabilities/attempt-runner/ExamClock";
import { useCountdown } from "@/capabilities/attempt-runner/useCountdown";
import { useAttemptSession, type AttemptSessionInput } from "@/capabilities/attempt-runner/useAttemptSession";
import { WaitingInLine } from "@/capabilities/attempt-runner/WaitingInLine";

export interface AttemptRunnerProps extends AttemptSessionInput {
  stationTitle: string;
  /** Markdown shown during the reading period. */
  brief?: string | null;
  patientName?: string;
  patientDetail?: string | null;
  simulationSeconds: number;
}

/**
 * One station, run.
 *
 * The only place in the product where a candidate speaks to a simulated
 * patient — whether they got here from a consumer mock, an institution's
 * circuit or an employer's exam. The arm decides what to pass in and what to
 * do with the result; everything between "start" and "ended" is here.
 */
export function AttemptRunner(props: AttemptRunnerProps) {
  const {
    stationTitle,
    brief,
    patientName = "Your patient",
    patientDetail,
    readingSeconds,
    simulationSeconds,
  } = props;

  const session = useAttemptSession(props);
  const mic = useMicPreflight(session.phase === "idle" || session.phase === "reading");

  const reading = useCountdown(readingSeconds, session.phase === "reading", () => {
    void session.startConsultation();
  });

  const consultation = useCountdown(simulationSeconds, session.phase === "live" && session.patientJoined, () => {
    void session.end();
  });

  // Give the patient a chance to close rather than being cut off mid-sentence.
  useEffect(() => {
    if (session.phase !== "live") return;
    if (consultation.secondsLeft === 60 || consultation.secondsLeft === 30) {
      session.warnTimeRemaining(consultation.secondsLeft);
    }
  }, [consultation.secondsLeft, session]);

  if (session.phase === "ended") {
    return (
      <Card title="Consultation finished">
        <p className="text-sm text-ink-muted">
          Your feedback is being prepared. It appears on this station as soon as it is ready.
        </p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold text-ink">{stationTitle}</h1>
        {session.phase === "reading" && (
          <ExamClock secondsLeft={reading.secondsLeft} label="Reading" />
        )}
        {session.phase === "live" && (
          <ExamClock secondsLeft={consultation.secondsLeft} label="Consultation" />
        )}
      </header>

      {session.error && <Alert tone="danger">{errorMessage(session.error)}</Alert>}
      {mic.message && <Alert tone="warning">{mic.message}</Alert>}

      {session.phase === "idle" && (
        <Card>
          <div className="flex flex-col gap-4">
            <p className="text-sm text-ink-muted">
              You will read the brief for {Math.round(readingSeconds / 60)} minutes, then speak to
              the patient for {Math.round(simulationSeconds / 60)}.
            </p>
            <div className="flex gap-2">
              <Button
                onClick={async () => {
                  if (mic.status !== "ready") await mic.request();
                  session.begin();
                }}
              >
                Start station
              </Button>
            </div>
          </div>
        </Card>
      )}

      {session.phase === "reading" && (
        <Card title="Candidate brief">
          <div className="flex flex-col gap-4">
            {brief ? (
              <div className="max-w-3xl text-sm leading-6 text-ink">
                <Markdown>{brief}</Markdown>
              </div>
            ) : (
              <p className="text-sm text-ink-muted">
                There is no written brief for this station. Go in when you are ready.
              </p>
            )}
            <div className="flex gap-2">
              <Button onClick={() => void session.startConsultation()}>
                I am ready, call the patient
              </Button>
              <Button variant="ghost" onClick={() => void session.abandon()}>
                Leave
              </Button>
            </div>
          </div>
        </Card>
      )}

      {session.phase === "connecting" && (
        <Card>
          <div className="flex items-center gap-3 text-sm text-ink-muted">
            <Spinner /> Connecting you to the patient…
          </div>
        </Card>
      )}

      {session.phase === "queued" && (
        <Card>
          <WaitingInLine position={session.queuePosition} onLeave={session.leaveQueue} />
        </Card>
      )}

      {session.phase === "live" && session.grant && (
        <VoiceRoom
          grant={session.grant}
          onConnected={session.attachRoom}
          onDisconnected={(unexpected) => {
            if (unexpected) void session.end();
          }}
        >
          <div className="flex flex-col items-center gap-5">
            <AgentTile name={patientName} detail={patientDetail} className="w-full max-w-sm" />
            <Button variant="danger" onClick={() => void session.end()}>
              <LuPhoneOff className="h-4 w-4" aria-hidden /> End consultation
            </Button>
          </div>
        </VoiceRoom>
      )}

      {session.phase === "ending" && (
        <Card>
          <div className="flex items-center gap-3 text-sm text-ink-muted">
            <Spinner /> Wrapping up…
          </div>
        </Card>
      )}

      {session.phase === "failed" && (
        <Card>
          <Button onClick={() => void session.startConsultation()}>Try again</Button>
        </Card>
      )}
    </div>
  );
}
