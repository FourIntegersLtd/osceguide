"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, AsyncBoundary, Button, ConfirmModal } from "@/foundation/ui";
import { b2cCard, b2cMutedBand } from "@/foundation/ui/productTokens";
import { errorMessage, useAsync } from "@/foundation/hooks";
import {
  cancelPeerSession,
  joinPeerSession,
  listAllMyPeerSessions,
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
export function UpcomingSessions({
  reloadKey,
  onOpenPracticeSession,
}: {
  reloadKey: number;
  onOpenPracticeSession?: (practiceSessionId: string) => void;
}) {
  const state = useAsync(async (signal) => {
    const items = await listAllMyPeerSessions(signal);
    return { items, next_cursor: null };
  }, [reloadKey]);
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [joining, setJoining] = useState<string | null>(null);

  const join = useCallback(
    async (session: PeerSession) => {
      setJoining(session.id);
      setNotice(null);
      setFailure(null);
      try {
        const updated = await joinPeerSession(session.id);
        const practiceId = updated.practice_session_id;
        if (practiceId && onOpenPracticeSession) {
          onOpenPracticeSession(practiceId);
          return;
        }
        setFailure("Could not start the practice room. Please try again.");
      } catch (cause) {
        setFailure(errorMessage(cause));
      } finally {
        setJoining(null);
      }
    },
    [onOpenPracticeSession],
  );

  return (
    <div className="space-y-4">
      {notice && <Alert tone="success">{notice}</Alert>}
      {failure && <Alert tone="danger">{failure}</Alert>}
      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{
          title: "No sessions yet",
          description: "Claim a slot from All Sessions to arrange your next practice session.",
        }}
      >
        {(page) => {
          const upcoming = page.items.filter(isShown);
          const past = page.items.filter((session) => !isShown(session));
          return (
            <div className="space-y-8">
              {upcoming.length > 0 && (
                <section>
                  <h3 className="mb-3 text-osce-body font-semibold text-osce-ink-900">Upcoming</h3>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
                    {upcoming.map((session) => (
                      <UpcomingSessionCard
                        key={session.id}
                        session={session}
                        onJoin={join}
                        isJoining={joining === session.id}
                        onCancelled={state.reload}
                      />
                    ))}
                  </div>
                </section>
              )}
              {past.length > 0 && (
                <section>
                  <h3 className="mb-3 text-osce-body font-semibold text-osce-ink-900">Past</h3>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
                    {past.map((session) => (
                      <PastSessionCard key={session.id} session={session} />
                    ))}
                  </div>
                </section>
              )}
              {upcoming.length === 0 && past.length > 0 && (
                <p className="text-osce-body text-b2c-text-secondary">
                  You have no future sessions. Post availability or claim a slot to practise with a colleague.
                </p>
              )}
            </div>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

function isShown(session: PeerSession): boolean {
  if (session.status === "cancelled" || session.status === "completed") return false;
  return session.status === "active" || !joinWindowClosed(session.starts_at);
}

function PastSessionCard({ session }: { session: PeerSession }) {
  const partner = session.partner_username ? `@${session.partner_username}` : "A colleague";
  return (
    <div className={`flex w-full min-w-0 flex-col p-3 text-osce-body sm:p-5 ${b2cCard}`}>
      <p className="text-osce-body text-b2c-text-muted">Practice session with</p>
      <p className="mt-1 font-semibold text-osce-ink-900">{partner}</p>
      <p className="mt-1 text-b2c-text-secondary">
        {longDate(session.starts_at)} at {meridiemTime(session.starts_at)}
      </p>
      <p className="mt-2 text-osce-caption text-b2c-text-muted">
        {session.exam_code.toUpperCase()}
        {session.user_role ? ` · You were the ${session.user_role}` : ""}
      </p>
    </div>
  );
}

function UpcomingSessionCard({
  session,
  onJoin,
  isJoining,
  onCancelled,
}: {
  session: PeerSession;
  onJoin: (session: PeerSession) => void;
  isJoining: boolean;
  onCancelled: () => void;
}) {
  const [now, setNow] = useState<number | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

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
  const ready = active || (now !== null && canJoin(session.starts_at, reference) && !joinWindowClosed(session.starts_at, reference));
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
          <span className="font-semibold">
            {session.partner_username ? `@${session.partner_username}` : "A colleague"}
          </span>
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

      {cancelError && (
        <Alert tone="danger" className="mb-2">
          {cancelError}
        </Alert>
      )}

      <div className="mt-auto flex flex-col items-stretch justify-between gap-3 border-t border-b2c-border pt-3 sm:flex-row sm:items-center sm:gap-2">
        <div className="flex items-center gap-2 text-osce-caption text-b2c-text-muted">
          <span>You are the {session.user_role}</span>
          <span>·</span>
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
        onConfirm={() => {
          setConfirming(false);
          void cancelPeerSession(session.id).then(onCancelled).catch(() => {
            setCancelError("Could not cancel this session. Try again or contact your partner.");
          });
        }}
        title="Cancel session?"
        tone="danger"
        message="Your partner will no longer see this session as booked. This cannot be undone."
        confirmText="Cancel session"
        cancelText="Keep session"
      />
    </div>
  );
}
