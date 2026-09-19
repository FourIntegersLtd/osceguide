"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, AsyncBoundary, Button, ConfirmModal } from "@/foundation/ui";
import { b2cCard, b2cMutedBand } from "@/foundation/ui/productTokens";
import { errorMessage, useAsync } from "@/foundation/hooks";
import {
  joinPeerSession,
  listMyPeerSessions,
  type PeerSession,
} from "@/capabilities/peer-practice/api";
import {
  canJoin,
  joinWindowClosed,
  JOIN_OPENS_MINUTES,
  longDate,
  meridiemTime,
  timeUntilJoin,
} from "@/capabilities/peer-practice/support/time";

/**
 * The sessions somebody has arranged, and the way into them.
 *
 * The retiring section refetched on a counter the parent incremented, which is
 * why claiming a slot and seeing it here were two separate round trips that
 * could disagree. It reloads itself now, and the parent asks for a reload
 * rather than owning one.
 */
export function UpcomingSessions({ reloadKey }: { reloadKey: number }) {
  const state = useAsync((signal) => listMyPeerSessions(signal), [reloadKey]);
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [joining, setJoining] = useState<string | null>(null);

  const join = useCallback(async (session: PeerSession) => {
    setJoining(session.id);
    setNotice(null);
    setFailure(null);
    try {
      await joinPeerSession(session.id);
      // The backend opens the session and names its room, but mints no token
      // for one — see docs/port-gaps.md. Saying so is better than a button
      // that appears to work and drops the person nowhere.
      setNotice(
        "You are checked in. Joining the call for an arranged session is not available yet — use Live Practice to be paired into a room now.",
      );
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setJoining(null);
    }
  }, []);

  return (
    <div className="space-y-4">
      {notice && <Alert tone="success">{notice}</Alert>}
      {failure && <Alert tone="danger">{failure}</Alert>}
      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.every((session) => !isShown(session))}
        empty={{
          title: "No upcoming sessions",
          description: "Claim a slot from the Available sessions to schedule a session!",
        }}
      >
        {(page) => (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
            {page.items.filter(isShown).map((session) => (
              <UpcomingSessionCard
                key={session.id}
                session={session}
                onJoin={join}
                isJoining={joining === session.id}
              />
            ))}
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}

function isShown(session: PeerSession): boolean {
  if (session.status === "cancelled" || session.status === "completed") return false;
  return !joinWindowClosed(session.starts_at);
}

function UpcomingSessionCard({
  session,
  onJoin,
  isJoining,
}: {
  session: PeerSession;
  onJoin: (session: PeerSession) => void;
  isJoining: boolean;
}) {
  const [now, setNow] = useState<number | null>(null);
  const [confirming, setConfirming] = useState(false);

  // The clock is read in an effect rather than during render, so the server and
  // the browser agree on the first frame; until it lands, measure from the
  // start itself so a valid card is never hidden.
  useEffect(() => {
    setNow(Date.now());
    const id = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => window.clearInterval(id);
  }, []);

  const reference = now ?? new Date(session.starts_at).getTime();
  const active = session.status === "active";
  const ready = active || canJoin(session.starts_at, reference);
  const until = timeUntilJoin(session.starts_at, reference);

  return (
    <div className={`flex w-full min-w-0 flex-col p-3 text-osce-body sm:p-5 ${b2cCard}`}>
      <div className="mb-3 flex items-center justify-between">
        <span className="text-osce-body text-b2c-text-muted">Practice session with</span>
        <span
          className={`rounded-full px-2 py-0.5 text-osce-caption font-medium ${
            active
              ? "bg-osce-success-bg text-osce-success-text"
              : ready
                ? "bg-osce-accent-subtle text-osce-accent-hover"
                : "bg-b2c-secondary text-b2c-text-secondary"
          }`}
        >
          {active ? "In Progress" : ready ? "Ready to Join" : "Upcoming"}
        </span>
      </div>

      <div className="mb-3">
        <p className="leading-relaxed text-osce-ink-900">
          <span className="font-semibold">A colleague</span>
        </p>
        <p className="mt-1 text-b2c-text-secondary">
          {longDate(session.starts_at)} at {meridiemTime(session.starts_at)}
        </p>
      </div>

      {!ready && until && (
        <div className={`mb-3 rounded-lg px-3 py-2 ${b2cMutedBand}`}>
          <p className="text-osce-body text-b2c-text-secondary">
            Session starts in <span className="font-medium text-osce-ink-900">{until}</span>
          </p>
          <p className="mt-0.5 text-osce-caption text-b2c-text-muted">
            You can join {JOIN_OPENS_MINUTES} minutes before the scheduled time
          </p>
        </div>
      )}

      <div className="mt-auto flex flex-col items-stretch justify-between gap-3 border-t border-b2c-border pt-3 sm:flex-row sm:items-center sm:gap-2">
        <div className="flex items-center gap-2 text-osce-caption text-b2c-text-muted">
          <span>{session.exam_code.toUpperCase()}</span>
        </div>
        <div className="flex w-full items-center gap-2 sm:w-auto">
          <Button
            type="button"
            variant="secondary"
            onClick={() => setConfirming(true)}
            className="flex-1 sm:flex-none"
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={() => onJoin(session)}
            disabled={(!ready && !active) || isJoining}
            className="flex-1 sm:flex-none"
          >
            {isJoining ? "Joining..." : active ? "Rejoin Session" : ready ? "Join Session" : "Not Yet"}
          </Button>
        </div>
      </div>

      <ConfirmModal
        isOpen={confirming}
        onCancel={() => setConfirming(false)}
        onConfirm={() => setConfirming(false)}
        title="Cancel session?"
        tone="danger"
        message="Cancelling an arranged session is not available yet. Let your partner know directly, and withdraw the slot if it was yours."
        confirmText="I understand"
        cancelButton={false}
      />
    </div>
  );
}
