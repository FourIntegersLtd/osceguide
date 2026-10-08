"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAsync, useMeEvents, useToast } from "@/foundation/hooks";
import { hasCode, isPlatformError } from "@/foundation/platform-client";
import { useCurrentExam, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities/SurfaceContext";
import {
  acceptPracticeMatch,
  declinePracticeMatch,
  joinPeerSession,
  readPracticeSession,
  listMyPeerSessions,
  MARKETPLACE_PAGE_SIZE,
} from "./api";
import { useQueue, type JoinOutcome, type Queue } from "./support/useQueue";
import { useQueuePersistence } from "./support/useQueuePersistence";
import { failureText, joinFailureText } from "./support/failure";
import { canJoin, joinWindowClosed } from "./support/time";
import {
  PartnerUnavailableModal,
  QueueExpiredModal,
  QueueIndicator,
  SearchingModal,
} from "./queue/modals";
import { MatchNotificationModal } from "./queue/MatchNotificationModal";
import { JoinablePeerSessionModal } from "./marketplace/JoinablePeerSessionModal";

type PeerContext = {
  queue: Queue;
  /** Go to a paired session's own page. */
  openSession: (practiceSessionId: string) => void;
  refresh: () => void;
  orgId: string | null;
};
const Context = createContext<PeerContext | null>(null);
export const usePeerPractice = () => useContext(Context);

/** Where a paired session lives, under the surface's own base path. */
export const SESSION_PATH = "/marketplace/session";

/**
 * Everything about practising with a person that outlives one screen: the
 * queue, the match prompt, and the "your session is ready" prompt. Mounted by
 * the consumer shell so a match found while reading the library still rings.
 */
export function PeerPracticeProvider({ children, orgId = null }: { children: ReactNode; orgId?: string | null }) {
  const { code } = useCurrentExam();
  const { session } = useSession();
  const scope = `${session?.user.id ?? "anonymous"}_${code}_${orgId ?? "public"}`;
  return <PeerPracticeScope key={scope} scope={scope} orgId={orgId}>{children}</PeerPracticeScope>;
}

function PeerPracticeScope({ children, scope, orgId }: { children: ReactNode; scope: string; orgId: string | null }) {
  const router = useRouter();
  const pathname = usePathname();
  const { hrefFor } = useSurface();
  const toast = useToast();
  const persistence = useQueuePersistence(scope);
  const baseQueue = useQueue(orgId, { entryId: persistence.entryId, onEntryId: persistence.remember });

  const [showSearching, setShowSearching] = useState(false);
  const [showIndicator, setShowIndicator] = useState(true);
  const [dismissedMatch, setDismissedMatch] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);
  const [partnerUnavailable, setPartnerUnavailable] = useState(false);

  const openSession = useCallback(
    (practiceSessionId: string) => router.push(hrefFor(`${SESSION_PATH}/${encodeURIComponent(practiceSessionId)}`)),
    [router, hrefFor],
  );
  const onSessionRoute = Boolean(pathname?.includes(`${SESSION_PATH}/`));

  /** The retiring context's toast for each way a join can go. */
  const announce = useCallback((outcome: JoinOutcome) => {
    switch (outcome.kind) {
      case "joined":
        setShowIndicator(true);
        setShowSearching(true);
        break;
      case "already_queued":
        toast.info("You're already in the queue", "You're already in the practice queue");
        setShowIndicator(true);
        setShowSearching(true);
        break;
      case "existing_session":
        toast.info("Rejoining your session", "You're already in an active practice session");
        openSession(outcome.sessionId);
        break;
      case "failed": {
        const { cause } = outcome;
        if (isPlatformError(cause) && (cause.status === 400 || cause.status === 422)) {
          toast.error("We couldn't join the queue", "Something in the request wasn't right. Please try again.");
        } else {
          toast.error("We couldn't join the practice queue", joinFailureText(cause));
        }
        break;
      }
      case "busy":
        break;
    }
  }, [toast, openSession]);

  const baseJoin = baseQueue.join;
  const join = useCallback(async (examCode: string) => {
    const outcome = await baseJoin(examCode);
    announce(outcome);
    return outcome;
  }, [baseJoin, announce]);
  const queue = useMemo<Queue>(() => ({ ...baseQueue, join }), [baseQueue, join]);

  const cancelSearch = useCallback(() => {
    setShowSearching(false);
    void queue.leave();
  }, [queue]);

  // A match rings in the browser too, once, when the tab is in the background.
  const matchId = queue.matchedSessionId;
  // A match ends the search: its modal gives way to the match's, and a later
  // requeue shows only the queue indicator, never two modals at once.
  const [searchEndedBy, setSearchEndedBy] = useState<string | null>(null);
  if (matchId && matchId !== searchEndedBy) {
    setSearchEndedBy(matchId);
    setShowSearching(false);
  }
  const notified = useRef<string | null>(null);
  useEffect(() => {
    if (!matchId || notified.current === matchId) return;
    notified.current = matchId;
    if ("Notification" in window && Notification.permission === "granted" && document.hidden) {
      const notification = new Notification("Practice partner found", {
        body: "A practice partner is available. Start your practice session now?",
        tag: matchId,
      });
      notification.onclick = () => { window.focus(); notification.close(); };
    }
  }, [matchId]);
  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      void Notification.requestPermission().catch(() => undefined);
    }
  }, []);

  const resetQueue = queue.reset;
  const acceptMatch = useCallback(async () => {
    if (!matchId || accepting) return;
    setAccepting(true);
    try {
      await acceptPracticeMatch(matchId);
      resetQueue();
      openSession(matchId);
    } catch (cause) {
      if (hasCode(cause, "partner_unavailable", "practice_session_ended")) {
        resetQueue();
        setPartnerUnavailable(true);
      } else {
        toast.error("We couldn't start your session", failureText(cause, "Please try again in a moment."));
      }
    } finally {
      setAccepting(false);
    }
  }, [matchId, accepting, resetQueue, openSession, toast]);

  const declineMatch = useCallback((keepModalOpen: boolean) => {
    if (!matchId) return;
    // The old client never waited on, or reported, a failed decline.
    void declinePracticeMatch(matchId).catch(() => undefined);
    if (keepModalOpen) return;
    resetQueue();
  }, [matchId, resetQueue]);

  const dismissMatch = useCallback(() => {
    setDismissedMatch(matchId);
    resetQueue();
  }, [matchId, resetQueue]);

  // The "your session is ready" prompt, for an arranged session in its window.
  const [dismissedBookings, setDismissedBookings] = useState<string[]>([]);
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);
  const bookings = useAsync((signal) => listMyPeerSessions({ when: "upcoming", limit: MARKETPLACE_PAGE_SIZE }, signal), []);
  const [now, setNow] = useState(Date.now);
  const refresh = bookings.reload;
  // A booking's own window opening is a clock, not an event — nothing on the server
  // fires when `starts_at` arrives, so `now` still ticks on its own timer. What used
  // to poll every 30s for a *changed* booking (matched, accepted, cancelled) now
  // reacts to those events, plus a `resync` on reconnect or the tab coming back.
  useMeEvents(
    ["practice.matched", "practice.accepted", "practice.session_updated"],
    useCallback(() => { setNow(Date.now()); refresh(); }, [refresh]),
  );
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => window.clearInterval(timer);
  }, []);
  const candidate = (bookings.data?.items ?? []).find((item) => !dismissedBookings.includes(item.id) &&
    (item.status === "active" || (item.status !== "cancelled" && item.status !== "completed" &&
      canJoin(item.starts_at, now) && !joinWindowClosed(item.starts_at, now))));
  const joinBooking = async () => {
    if (!candidate || joining) return;
    setJoining(true);
    setJoinError(null);
    try {
      const result = await joinPeerSession(candidate.id);
      if (result.practice_session_id) {
        setDismissedBookings((ids) => [...ids, candidate.id]);
        openSession(result.practice_session_id);
      } else {
        setJoinError("Invalid session data received. Please try again.");
      }
    } catch (cause) {
      setJoinError(
        hasCode(cause, "too_early_to_join")
          ? failureText(cause, "Too early to join.")
          : failureText(cause, "Failed to join session. Please try again."),
      );
    } finally {
      setJoining(false);
    }
  };

  const showMatch = Boolean(matchId) && dismissedMatch !== matchId;
  // The match's own answer-by time, from the server.
  const match = useAsync((signal) => (matchId ? readPracticeSession(matchId, signal) : Promise.resolve(null)), [matchId]);
  const waiting = queue.phase === "waiting";

  return (
    <Context.Provider value={{ queue, openSession, refresh, orgId }}>
      {children}

      {showSearching && waiting && (
        <SearchingModal onCancelSearch={cancelSearch} onDismiss={() => setShowSearching(false)} />
      )}

      {waiting && !showSearching && showIndicator && (
        <QueueIndicator onCancel={() => void queue.leave()} onDismiss={() => setShowIndicator(false)} />
      )}

      {showMatch && matchId && (
        <MatchNotificationModal
          key={matchId}
          sessionId={matchId}
          expiresAt={match.data?.id === matchId ? match.data.accept_expires_at ?? null : null}
          isAccepting={accepting}
          onAccept={() => void acceptMatch()}
          onDecline={() => declineMatch(false)}
          onAutoDecline={() => declineMatch(true)}
          onDismiss={dismissMatch}
        />
      )}

      {queue.expired && <QueueExpiredModal onClose={queue.reset} />}

      {partnerUnavailable && <PartnerUnavailableModal onClose={() => setPartnerUnavailable(false)} />}

      {candidate && !showMatch && !onSessionRoute && (
        <JoinablePeerSessionModal
          session={candidate}
          isJoining={joining}
          joinError={joinError}
          onJoin={() => void joinBooking()}
          onDismiss={() => { setDismissedBookings((ids) => [...ids, candidate.id]); setJoinError(null); }}
        />
      )}
    </Context.Provider>
  );
}
