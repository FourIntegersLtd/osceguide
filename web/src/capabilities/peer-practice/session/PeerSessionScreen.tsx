"use client";

import { useCallback, useState } from "react";
import { HiOutlineUsers } from "react-icons/hi2";
import {
  Alert,
  B2CErrorState,
  Button,
  ConfirmModal,
  LoadingSpinner,
} from "@/foundation/ui";
import { b2cCard, b2cCardPadding } from "@/foundation/ui/productTokens";
import { errorMessage } from "@/foundation/hooks";
import { AgentTile, VoiceRoom } from "@/foundation/livekit";
import { SessionHeader } from "@/capabilities/peer-practice/session/SessionHeader";
import { usePeerSession } from "@/capabilities/peer-practice/support/usePeerSession";

/**
 * The paired session itself.
 *
 * Two people, one room, and the only two things the server will tell us about
 * it: which part each is playing, and when it started. The retiring runner put
 * a reading brief and a patient script beside the call, and neither survives
 * the port — `platform-api` does not serve the station a peer session is about.
 * That is the one thing missing from this screen and it is written down in
 * `docs/port-gaps.md` rather than faked.
 */
export function PeerSessionScreen({
  sessionId,
  onLeave,
}: {
  sessionId: string;
  onLeave: () => void;
}) {
  const session = usePeerSession(sessionId);
  const [confirmingEnd, setConfirmingEnd] = useState(false);

  const confirmEnd = useCallback(async () => {
    setConfirmingEnd(false);
    await session.end("ended_by_participant");
  }, [session]);

  if (session.phase === "loading") {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (session.loadError || !session.session) {
    return (
      <B2CErrorState
        title="We couldn't load this practice session"
        description={session.loadError ? errorMessage(session.loadError) : undefined}
        onRetry={session.reload}
        secondaryAction={
          <Button type="button" variant="secondary" size="sm" onClick={onLeave}>
            Back to practice
          </Button>
        }
      />
    );
  }

  const role = session.session.my_role;

  if (session.phase === "ended") {
    return (
      <div className="mx-auto max-w-2xl px-3 py-4 text-center sm:px-4 sm:py-6">
        <h2 className="mb-3 text-osce-body font-bold text-osce-ink-900 sm:mb-4">
          Session Completed
        </h2>
        <p className="mb-4 px-2 text-osce-body text-b2c-text-secondary sm:mb-6">
          Thank you for participating in the practice session!
        </p>
        {session.error && (
          <Alert tone="warning" className="mb-4 text-left">
            {errorMessage(session.error)}
          </Alert>
        )}
        <Button type="button" variant="primary" size="md" onClick={onLeave}>
          Back to practice
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col overflow-hidden rounded-osce-lg border border-b2c-border bg-b2c-surface-muted">
      <SessionHeader
        role={role}
        phaseLabel={session.phase === "live" ? "Live Consultation" : "You have been matched"}
        elapsed={session.elapsed}
        running={session.phase === "live"}
        busy={session.busy}
        onEndSession={() => setConfirmingEnd(true)}
      />

      <div className="flex-1 p-3 sm:p-4">
        {session.dropped && (
          <Alert tone="warning" className="mb-3">
            The call dropped. Rejoin when you are ready — your partner is still in the room.
          </Alert>
        )}
        {session.error && (
          <Alert tone="danger" className="mb-3">
            {errorMessage(session.error)}
          </Alert>
        )}
        {session.mic.message && (
          <Alert tone="warning" className="mb-3">
            {session.mic.message}
          </Alert>
        )}

        {session.phase === "live" && session.grant ? (
          <VoiceRoom grant={session.grant} onDisconnected={session.noteDisconnected}>
            <div className="flex flex-col items-center gap-4">
              <AgentTile
                name="Your partner"
                detail={
                  role === "doctor"
                    ? "You are the doctor · they are playing the patient"
                    : "You are the patient · they are the doctor"
                }
                className="w-full max-w-sm"
              />
            </div>
          </VoiceRoom>
        ) : (
          <div className={`mx-auto max-w-md text-center ${b2cCard} ${b2cCardPadding}`}>
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-osce-accent-subtle ring-2 ring-osce-accent/20">
              <HiOutlineUsers className="h-8 w-8 text-osce-accent" />
            </div>
            <h2 className="mb-2 text-osce-subheading font-semibold text-osce-ink-900">
              You have a practice partner
            </h2>
            <p className="mb-6 text-b2c-text-secondary">
              You are the <span className="font-semibold">{role}</span> for this session. Join the
              call when you are ready — the timer starts once you are both in the room.
            </p>
            <Button
              type="button"
              variant="commit"
              size="md"
              fullWidth
              isLoading={session.busy}
              onClick={() => void session.connect()}
            >
              Join the call
            </Button>
            <button
              type="button"
              onClick={onLeave}
              className="mt-3 text-osce-body text-b2c-text-muted underline-offset-2 hover:underline"
            >
              Not now
            </button>
          </div>
        )}
      </div>

      <ConfirmModal
        isOpen={confirmingEnd}
        onCancel={() => setConfirmingEnd(false)}
        onConfirm={() => void confirmEnd()}
        tone="danger"
        title="End Practice Session"
        message="Ending the session closes the room for both of you. Are you sure you want to end the session?"
        confirmText="Yes, End Session"
        cancelText="Cancel"
        isLoading={session.busy}
      />
    </div>
  );
}
