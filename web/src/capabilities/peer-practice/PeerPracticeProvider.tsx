"use client";

import { createContext, lazy, Suspense, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { Alert, Button, LoadingSpinner } from "@/foundation/ui";
import { useAsync, errorMessage } from "@/foundation/hooks";
import { useCurrentExam, useSession } from "@/foundation/session";
import { joinPeerSession, listAllMyPeerSessions } from "./api";
import { useQueue } from "./support/useQueue";
import { useQueuePersistence } from "./support/useQueuePersistence";
import { canJoin, joinWindowClosed } from "./support/time";
import { QueueOverlay } from "./queue/QueueOverlay";
import { MatchNotificationModal } from "./queue/MatchNotificationModal";
import { JoinablePeerSessionModal } from "./marketplace/JoinablePeerSessionModal";

const PeerSessionScreen = lazy(() => import("./session/PeerSessionScreen").then((module) => ({ default: module.PeerSessionScreen })));
type PeerContext = { queue: ReturnType<typeof useQueue>; openSession: (id: string) => void; refresh: () => void; orgId: string | null };
const Context = createContext<PeerContext | null>(null);
export const usePeerPractice = () => useContext(Context);

export function PeerPracticeProvider({ children, orgId = null }: { children: ReactNode; orgId?: string | null }) {
  const { code } = useCurrentExam();
  const { session } = useSession();
  const scope = `${session?.user.id ?? "anonymous"}_${code}_${orgId ?? "public"}`;
  return <PeerPracticeScope key={scope} scope={scope} orgId={orgId}>{children}</PeerPracticeScope>;
}
function PeerPracticeScope({ children, scope, orgId }: { children: ReactNode; scope: string; orgId: string | null }) {
  const persistence = useQueuePersistence(scope);
  const [openId, setOpenId] = useState<string | null>(null);
  const queue = useQueue(orgId, { entryId: persistence.entryId, onEntryId: persistence.remember, onExistingSession: setOpenId });
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);
  const bookings = useAsync((signal) => listAllMyPeerSessions(signal), []);
  const [now, setNow] = useState(Date.now);
  const refresh = bookings.reload;
  useEffect(() => {
    const timer = window.setInterval(() => { setNow(Date.now()); refresh(); }, 30_000);
    window.addEventListener("focus", refresh);
    return () => { window.clearInterval(timer); window.removeEventListener("focus", refresh); };
  }, [refresh]);
  const candidate = (bookings.data ?? []).find((item) => !dismissed.includes(item.id) &&
    (item.status === "active" || (item.status !== "cancelled" && item.status !== "completed" &&
      canJoin(item.starts_at, now) && !joinWindowClosed(item.starts_at, now))));
  const leave = useCallback(() => {
    setOpenId(null); queue.reset(); refresh();
  }, [queue, refresh]);
  const join = async () => {
    if (!candidate || joining) return;
    setJoining(true); setJoinError(null);
    try {
      const result = await joinPeerSession(candidate.id);
      if (result.practice_session_id) {
        setDismissed((ids) => [...ids, candidate.id]);
        setOpenId(result.practice_session_id);
      } else setJoinError("Could not open the practice room. Please try again.");
    } catch (cause) { setJoinError(errorMessage(cause)); }
    finally { setJoining(false); }
  };
  return <Context.Provider value={{ queue, openSession: setOpenId, refresh: bookings.reload, orgId }}>
    <div inert={Boolean(openId)}>{children}</div>
    {bookings.error && <Alert tone="warning">Could not check upcoming practice sessions. <Button size="sm" onClick={bookings.reload}>Retry</Button></Alert>}
    {openId ? <div className="fixed inset-0 z-[60] overflow-auto bg-canvas" role="dialog" aria-label="Peer practice session" aria-modal="true">
      <Suspense fallback={<LoadingSpinner />}><PeerSessionScreen key={openId} sessionId={openId} onLeave={leave}
        onRequeue={(sessionExam) => { leave(); void queue.join(sessionExam); }} /></Suspense>
    </div> : <>
      <QueueOverlay key={queue.status?.entry_id ?? "idle"} queue={queue} />
      {queue.matchedSessionId ? <MatchNotificationModal key={queue.matchedSessionId} sessionId={queue.matchedSessionId}
        onAccept={() => setOpenId(queue.matchedSessionId)} onDeclined={queue.reset} /> :
        candidate && <JoinablePeerSessionModal session={candidate} isJoining={joining} joinError={joinError}
          onJoin={() => void join()} onDismiss={() => { setDismissed((ids) => [...ids, candidate.id]); setJoinError(null); }} />}
    </>}
  </Context.Provider>;
}
