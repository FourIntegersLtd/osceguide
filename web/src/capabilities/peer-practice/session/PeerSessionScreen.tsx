"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { HiOutlineUsers } from "react-icons/hi2";
import { Button, ConfirmModal } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import { VoiceRoom } from "@/foundation/livekit";
import { PeerVideoPanel } from "@/foundation/livekit/PeerVideoPanel";
import { useSurface } from "@/capabilities/SurfaceContext";
import { usePeerPractice, SESSION_PATH } from "../PeerPracticeProvider";
import { LivePracticeButton } from "../queue/LivePracticeButton";
import { PartnerLeftModal, PartnerUnavailableModal } from "../queue/modals";
import { usePeerSession, type PeerSessionState } from "../support/usePeerSession";
import { ABANDONED_REASON, endingAbandons, sessionExit, type RunnerPhase } from "../support/sessionState";
import { phaseDurations, formatCountdown } from "../support/examTimers";
import { failureText } from "../support/failure";
import type { PracticeSession } from "../api";
import { SessionHeader } from "./SessionHeader";
import { ConsultationPanel, PreparationPanel } from "./PreparationPanel";
import { NoShowGuidelines } from "./SafetyActions";
import { PhaseModals } from "./modals";

/**
 * A live practice session with another candidate, on its own route: waiting
 * for the partner, the reading phase, the video consultation and the debrief.
 *
 * Every phase and every clock comes from the server. When the session ends
 * this screen only decides where to go next (`sessionExit`): the feedback
 * page, the dashboard, or — when the partner left early — a requeue offer.
 * A match the partner declined or never answered after this side accepted
 * says "Session no longer available"; the server has already requeued them.
 */
export function PeerSessionScreen({ sessionId }: { sessionId: string }) {
  const state = usePeerSession(sessionId);
  const router = useRouter();
  const { hrefFor } = useSurface();
  const peers = usePeerPractice();
  const toast = useToast();
  const [confirmingEnd, setConfirmingEnd] = useState(false);
  const [requeuing, setRequeuing] = useState(false);

  const dashboard = hrefFor("");
  const feedbackHref = hrefFor(`${SESSION_PATH}/${encodeURIComponent(sessionId)}/feedback`);
  const exit = sessionExit(state.session, state.endedByMe);
  const exitKind = exit.kind;

  useEffect(() => {
    if (exitKind === "feedback") router.replace(feedbackHref);
    if (exitKind === "dashboard") router.replace(dashboard);
  }, [exitKind, router, feedbackHref, dashboard]);
  // The server requeued this side when the match fell through; follow that place.
  const requeuedEntry = exit.kind === "requeued" ? exit.entryId : null;
  const adopt = peers?.queue.adopt;
  useEffect(() => {
    if (requeuedEntry && adopt) adopt(requeuedEntry);
  }, [requeuedEntry, adopt]);

  if (state.runnerPhase === "loading" && !state.loadError) return <SessionLoading />;
  if (!state.session) {
    return <SessionError message={state.loadError ? errorMessage(state.loadError) : null} onReturn={() => router.push(dashboard)} />;
  }
  const session = state.session;
  const role = session.my_role === "patient" ? "patient" : "doctor";
  const phase = state.runnerPhase;

  const confirmEnd = async () => {
    const abandons = endingAbandons(phase, state.remaining);
    const failure = await state.end(abandons ? ABANDONED_REASON : "ended_by_participant");
    setConfirmingEnd(false);
    if (failure) toast.error("We couldn't end the session cleanly", failureText(failure, "Please try again."));
  };

  const requeue = async () => {
    if (!peers || requeuing) return;
    setRequeuing(true);
    const outcome = await peers.queue.join(session.exam_code);
    if (outcome.kind === "failed") {
      setRequeuing(false);
      return;
    }
    router.push(dashboard);
  };

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-b2c-surface-muted">
      <SessionHeader
        sessionId={sessionId}
        role={role}
        phase={phase}
        stationName={session.station?.title ?? ""}
        seconds={headerSeconds(session, phase, state.remaining)}
        onEndSession={() => setConfirmingEnd(true)}
      />

      <ConfirmModal
        isOpen={confirmingEnd}
        onCancel={() => setConfirmingEnd(false)}
        onConfirm={() => void confirmEnd()}
        title="End Practice Session"
        message={<EndSessionMessage role={role} phase={phase} remaining={state.remaining ?? 0} />}
        confirmText="Yes, End Session"
        cancelText="Cancel"
        isLoading={state.busy}
      />

      {exit.kind === "requeued" && <PartnerUnavailableModal onClose={() => router.replace(dashboard)} />}

      {exit.kind === "partner_gone" && (
        <PartnerLeftModal
          reason={exit.reason}
          isRequeuing={requeuing}
          onRequeue={peers ? () => void requeue() : undefined}
          onGoToDashboard={() => router.push(dashboard)}
        />
      )}

      <PhaseModals phase={phase} remaining={state.remaining} preparationStarted={session.preparation_started_at} />

      <div
        className={`min-h-0 flex-1 ${phase === "consultation" || phase === "debrief" ? "overflow-y-auto" : "overflow-hidden"} lg:overflow-hidden`}
      >
        {phase === "waiting_partner" && (
          <WaitingForPartner
            sessionId={sessionId}
            afterReport={peers ? <LivePracticeButton queue={peers.queue} examCode={session.exam_code} /> : null}
          />
        )}
        {phase === "preparation" && <PreparationPanel session={session} />}
        {(phase === "consultation" || phase === "debrief") && (
          <div className="flex h-full min-h-0 flex-col bg-b2c-secondary lg:flex-row lg:overflow-hidden">
            <div className="h-[38vh] min-h-[280px] w-full flex-shrink-0 bg-b2c-secondary sm:h-[42vh] sm:min-h-[320px] lg:h-full lg:min-h-0 lg:w-3/5 lg:overflow-hidden">
              <VideoArea state={state} role={role} />
            </div>
            <div className="flex min-h-[55vh] w-full flex-1 flex-col overflow-hidden border-t border-b2c-border bg-osce-surface sm:min-h-[58vh] lg:h-full lg:min-h-0 lg:w-2/5 lg:border-l lg:border-t-0">
              <div className="flex h-full min-h-0 flex-1 flex-col">
                <ConsultationPanel session={session} debrief={phase === "debrief"} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * The seconds the header shows. While a phase runs it is the server's
 * deadline; before the preparation clock starts it is the phase's full length,
 * which is what the header showed while waiting.
 */
function headerSeconds(session: PracticeSession, phase: RunnerPhase, remaining: number | null): number {
  if (remaining !== null) return remaining;
  const durations = phaseDurations(session.exam_code);
  if (phase === "debrief") return durations.debrief;
  if (phase === "consultation") return durations.consultation;
  return durations.preparation;
}

/**
 * The call. It connects on its own when the consultation starts and again if
 * the connection drops, as the retiring room did.
 */
function VideoArea({ state, role }: { state: PeerSessionState; role: "doctor" | "patient" }) {
  const { grant, busy, dropped, connect, mic } = state;
  useEffect(() => {
    if (dropped && !busy && !grant) void connect();
  }, [dropped, busy, grant, connect]);

  const failure = state.error ?? null;
  if (!grant && !busy && (failure || mic.message)) {
    return (
      <div className="flex h-full items-center justify-center bg-osce-canvas">
        <div className="text-center">
          <div className="mb-2 text-osce-body font-semibold text-osce-danger">Video Session Error</div>
          <p className="mb-4 text-osce-ink-600">
            {failure ? failureText(failure, "Failed to start video session") : mic.message ?? "Failed to start video session"}
          </p>
          <Button type="button" variant="primary" size="md" onClick={() => void connect()}>
            Try Again
          </Button>
        </div>
      </div>
    );
  }
  if (!grant) {
    return (
      <div className="flex h-full items-center justify-center bg-osce-canvas">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-osce-accent-hover" />
          <p className="text-osce-ink-600">Connecting to video session...</p>
        </div>
      </div>
    );
  }
  return (
    <div className="h-full">
      <VoiceRoom className="h-full" grant={grant} video onDisconnected={state.noteDisconnected}>
        <PeerVideoPanel role={role} />
      </VoiceRoom>
    </div>
  );
}

function WaitingForPartner({ sessionId, afterReport }: { sessionId: string; afterReport: ReactNode }) {
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-3 py-4 sm:px-4 sm:py-6">
        <div className="flex min-h-[400px] flex-col items-center justify-center text-center">
          <div className="mb-4">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-osce-accent-subtle ring-2 ring-osce-accent/20">
              <HiOutlineUsers className="h-8 w-8 text-osce-accent" />
            </div>
          </div>
          <h2 className="mb-2 text-osce-subheading font-semibold text-osce-ink-900">Waiting for your partner to join...</h2>
          <p className="mb-6 text-b2c-text-secondary">The timer will start once both users have joined the session.</p>
          <NoShowGuidelines sessionId={sessionId} afterReport={afterReport} />
        </div>
      </div>
    </div>
  );
}

/**
 * What ending now means, in the retiring client's words. A doctor is told
 * whether feedback will be generated; a patient only how much time is left.
 */
function EndSessionMessage({ role, phase, remaining }: { role: "doctor" | "patient"; phase: RunnerPhase; remaining: number }) {
  const preparing = phase === "waiting_partner" || phase === "preparation";
  if (role === "patient") {
    // The retiring client meant to show these but had them commented out, so
    // a patient saw an empty dialog.
    if (preparing) {
      return <p>Are you sure you want to end the session? Your partner will be given the option to be requeued.</p>;
    }
    if (phase === "consultation") {
      return (
        <p>
          You have <span className="font-semibold">{formatCountdown(remaining)}</span> remaining. Are you sure you want
          to end the session?
        </p>
      );
    }
    return <p>Are you sure you want to end this practice session?</p>;
  }
  if (preparing) {
    return (
      <div className="space-y-2">
        <p>
          If you end the session now, it will be marked as abandoned and{" "}
          <span className="font-semibold">no feedback will be generated</span>. Your partner will be given the option to
          be requeued.
        </p>
        <p>Are you sure you want to end the session?</p>
      </div>
    );
  }
  if (phase === "consultation" && remaining > 180) {
    return (
      <div className="space-y-2">
        <p>
          You have <span className="font-semibold">{formatCountdown(remaining)}</span> remaining in the consultation. If
          you end the session now, it will be marked as abandoned and{" "}
          <span className="font-semibold">no feedback will be generated</span>. Your partner will be given the option to
          be requeued.
        </p>
        <p>Are you sure you want to end the session?</p>
      </div>
    );
  }
  if (phase === "consultation") {
    return (
      <div className="space-y-2">
        <p>
          You have <span className="font-semibold">{formatCountdown(remaining)}</span> remaining in the consultation.
        </p>
        <p>
          <span className="font-semibold">Feedback will be generated</span> and should be available within{" "}
          <span className="font-semibold">View All Sessions</span> under the <span className="font-semibold">Practice</span>{" "}
          tab in about <span className="font-semibold">60-90 seconds</span>.
        </p>
        <p>Are you sure you want to end the session?</p>
      </div>
    );
  }
  return <p>Are you sure you want to end this practice session?</p>;
}

function SessionLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-b2c-surface-muted px-4">
      <div className="text-center">
        <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-b-2 border-osce-accent sm:h-12 sm:w-12" />
        <p className="text-osce-body text-b2c-text-secondary">Loading practice session...</p>
      </div>
    </div>
  );
}

function SessionError({ message, onReturn }: { message: string | null; onReturn: () => void }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-b2c-surface-muted px-4">
      <div className="mx-auto max-w-md text-center">
        <div className="mb-4 px-2 text-osce-body font-semibold text-osce-danger">{message || "Session not found"}</div>
        <Button type="button" variant="primary" size="md" onClick={onReturn}>
          Return to Dashboard
        </Button>
      </div>
    </div>
  );
}
