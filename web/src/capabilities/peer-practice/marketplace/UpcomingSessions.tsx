"use client";

import { useCallback, useEffect, useState } from "react";
import Alert from "@/foundation/forms/Alert";
import { AsyncBoundary, Button, ConfirmModal } from "@/foundation/ui";
import { b2cCard, b2cMutedBand } from "@/foundation/ui/productTokens";
import { useCursorPages } from "@/foundation/hooks";
import {
  cancelPeerSession,
  joinPeerSession,
  listMyPeerSessions,
  MARKETPLACE_PAGE_SIZE,
  type PeerSession,
} from "@/capabilities/peer-practice/api";
import { ListLoadError, ListLoading } from "@/capabilities/peer-practice/marketplace/listStates";
import { failureText } from "@/capabilities/peer-practice/support/failure";
import { hasCode } from "@/foundation/platform-client";
import {
  canJoin,
  JOIN_OPENS_MINUTES,
  longDate,
  meridiemTime,
  timeUntilJoin,
} from "@/capabilities/peer-practice/support/time";

type Notice = { id: number; type: "success" | "error"; text: string };

/**
 * The sessions somebody has arranged, and the way into them.
 *
 * `when=upcoming` is the server's own definition — cancelled, completed or
 * more than an hour past their start are left out there, not here. A page at
 * a time, so this no longer walks every booking to find the live ones.
 */
export function UpcomingSessions({
  reloadKey,
  onOpenPracticeSession,
}: {
  reloadKey: number;
  onOpenPracticeSession: (practiceSessionId: string) => void;
}) {
  const pages = useCursorPages(
    (cursor, signal) =>
      listMyPeerSessions({ cursor, limit: MARKETPLACE_PAGE_SIZE, when: "upcoming" }, signal),
    [reloadKey],
  );
  const state = pages.state;
  const [notice, setNotice] = useState<Notice | null>(null);
  const [joiningId, setJoiningId] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [now, setNow] = useState<number | null>(null);

  // Read the clock after hydration so the server and the browser agree.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  const say = useCallback((type: Notice["type"], text: string) => {
    setNotice((previous) => ({ id: (previous?.id ?? 0) + 1, type, text }));
  }, []);

  const join = useCallback(
    async (session: PeerSession) => {
      setJoiningId(session.id);
      setNotice(null);
      try {
        const updated = await joinPeerSession(session.id);
        if (!updated.practice_session_id) {
          say("error", "Invalid session data received. Please try again.");
          setJoiningId(null);
          return;
        }
        onOpenPracticeSession(updated.practice_session_id);
      } catch (cause) {
        say(
          "error",
          hasCode(cause, "too_early_to_join")
            ? failureText(cause, "Too early to join.")
            : failureText(cause, "Failed to join session. Please try again."),
        );
        setJoiningId(null);
      }
    },
    [onOpenPracticeSession, say],
  );

  const reload = state.reload;
  const cancel = useCallback(
    async (sessionId: string) => {
      setCancellingId(sessionId);
      setNotice(null);
      try {
        await cancelPeerSession(sessionId);
        say("success", "Session cancelled. Your partner has been notified.");
        reload();
      } catch (cause) {
        say("error", failureText(cause, "Failed to cancel session. Please try again."));
      } finally {
        setCancellingId(null);
      }
    },
    [reload, say],
  );

  return (
    <AsyncBoundary
      state={state}
      isEmpty={() => false}
      loading={<ListLoading />}
      failure={(_error, retry) => (
        <ListLoadError message="Failed to load upcoming sessions. Please try again." onRetry={retry} />
      )}
    >
      {(sessions) => {
        if (sessions.length === 0) {
          return (
            <>
              {notice && <Alert key={notice.id} message={notice.text} type={notice.type} className="mb-4" />}
              <div className="py-12 text-center">
                <p className="mb-2 text-osce-body text-b2c-text-muted">No upcoming sessions</p>
                <p className="text-osce-body text-b2c-text-muted">
                  Claim a slot from the Available sessions to schedule a session!
                </p>
              </div>
            </>
          );
        }
        return (
          <div className="space-y-4">
            {notice && <Alert key={notice.id} message={notice.text} type={notice.type} className="mb-4" />}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
              {sessions.map((session) => (
                <UpcomingSessionCard
                  key={session.id}
                  session={session}
                  now={now}
                  onJoin={join}
                  onCancel={(id) => void cancel(id)}
                  isJoinLoading={joiningId === session.id}
                  isCancelLoading={cancellingId === session.id}
                />
              ))}
            </div>
            {pages.moreError ? (
              <p className="text-osce-body text-osce-danger">
                Could not load more sessions: {pages.moreError.message}
              </p>
            ) : null}
            {pages.hasMore ? (
              <div className="flex justify-center">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={pages.loadingMore}
                  onClick={pages.loadMore}
                >
                  {pages.loadingMore ? "Loading…" : "Load more sessions"}
                </Button>
              </div>
            ) : null}
          </div>
        );
      }}
    </AsyncBoundary>
  );
}

function UpcomingSessionCard({
  session,
  now,
  onJoin,
  onCancel,
  isJoinLoading,
  isCancelLoading,
}: {
  session: PeerSession;
  now: number | null;
  onJoin: (session: PeerSession) => void;
  onCancel: (sessionId: string) => void;
  isJoinLoading: boolean;
  isCancelLoading: boolean;
}) {
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const isActive = session.status === "active";
  const joinable = now !== null && canJoin(session.starts_at, now);
  const until = now === null ? null : timeUntilJoin(session.starts_at, now);

  return (
    <div className={`group flex w-full min-w-0 flex-col p-3 text-osce-body sm:p-5 ${b2cCard}`}>
      <div className="mb-3 flex items-center justify-between">
        <span className="text-osce-body text-b2c-text-muted">Practice session with</span>
        <span
          className={`rounded-full px-2 py-0.5 text-osce-caption font-medium ${
            isActive
              ? "bg-osce-success-bg text-osce-success-text"
              : joinable
                ? "bg-osce-accent-subtle text-osce-accent-hover"
                : "bg-b2c-secondary text-b2c-text-secondary"
          }`}
        >
          {isActive ? "In Progress" : joinable ? "Ready to Join" : "Upcoming"}
        </span>
      </div>

      <div className="mb-3">
        <p className="leading-relaxed text-osce-ink-900">
          <span className="font-semibold">@{session.partner_username}</span>
        </p>
        <p className="mt-1 text-b2c-text-secondary">
          {longDate(session.starts_at)} at {meridiemTime(session.starts_at)}
        </p>
      </div>

      {!joinable && !isActive && until && (
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
          <span>You are the {session.user_role}</span>
        </div>
        <div className="flex w-full items-center gap-2 sm:w-auto">
          <Button
            type="button"
            variant="secondary"
            onClick={() => setShowCancelConfirm(true)}
            disabled={isCancelLoading}
            className="flex-1 sm:flex-none"
          >
            {isCancelLoading ? "Cancelling..." : "Cancel"}
          </Button>
          <Button
            type="button"
            onClick={() => onJoin(session)}
            disabled={(!joinable && !isActive) || isJoinLoading}
            className="flex-1 sm:flex-none"
          >
            {isJoinLoading ? "Joining..." : isActive ? "Rejoin Session" : joinable ? "Join Session" : "Not Yet"}
          </Button>
        </div>
      </div>

      <ConfirmModal
        isOpen={showCancelConfirm}
        onCancel={() => setShowCancelConfirm(false)}
        onConfirm={() => {
          onCancel(session.id);
          setShowCancelConfirm(false);
        }}
        title="Cancel session?"
        message={
          <>
            Are you sure you want to cancel this session with{" "}
            <span className="font-medium">@{session.partner_username}</span>? Your partner will be
            notified.
          </>
        }
        confirmText="Yes, cancel session"
        cancelText="Keep session"
      />
    </div>
  );
}
