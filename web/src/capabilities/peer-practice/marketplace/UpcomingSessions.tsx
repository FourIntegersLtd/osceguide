"use client";

import { useCallback, useEffect, useState } from "react";
import Alert from "@/foundation/forms/Alert";
import { HiOutlineVideoCamera } from "react-icons/hi2";
import { AsyncBoundary, Badge, Button, ConfirmModal, productTokens } from "@/foundation/ui";
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
import { b2cPanelDivided } from "@/foundation/ui/productTokens";

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
        say("error", failureText(cause, "Could not cancel the session. Try again."));
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
              <div className="rounded-osce-lg border border-dashed border-osce-border px-5 py-10 text-center">
                <p className="text-osce-body font-medium text-osce-ink-900">No upcoming sessions</p>
                <p className="mt-1 text-osce-meta text-b2c-text-muted">
                  Claim a slot from the available sessions to schedule one.
                </p>
              </div>
            </>
          );
        }
        return (
          <div className="space-y-4">
            {notice && <Alert key={notice.id} message={notice.text} type={notice.type} className="mb-4" />}
            <p className={productTokens.b2cMonoEyebrow}>Upcoming</p>
            <ul className={b2cPanelDivided}>
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
            </ul>
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
    <li className="flex flex-wrap items-center gap-3 px-4 py-3">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control bg-b2c-surface-muted text-b2c-text-muted">
        <HiOutlineVideoCamera className="h-4 w-4" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-osce-body font-medium text-osce-ink-900">
          Practice session with @{session.partner_username}
        </p>
        <p className="text-osce-meta text-b2c-text-muted">
          {longDate(session.starts_at)} at {meridiemTime(session.starts_at)} · You are the {session.user_role}
          {!joinable && !isActive && until ? ` · Opens ${JOIN_OPENS_MINUTES} min before, starts in ${until}` : ""}
        </p>
      </div>
      <Badge tone={isActive ? "success" : joinable ? "accent" : "neutral"} dot={isActive || joinable}>
        {isActive ? "In progress" : joinable ? "Ready to join" : "Upcoming"}
      </Badge>
      <div className="flex items-center gap-2">
        {isActive || joinable ? (
          <Button type="button" size="sm" onClick={() => onJoin(session)} isLoading={isJoinLoading}>
            {isActive ? "Rejoin session" : "Join session"}
          </Button>
        ) : null}
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => setShowCancelConfirm(true)}
          isLoading={isCancelLoading}
        >
          Cancel
        </Button>
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
    </li>
  );
}
