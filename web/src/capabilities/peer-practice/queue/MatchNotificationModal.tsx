"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Modal, ModalContent, ModalLead, ModalFooterActions, ModalPrimaryButton, ModalSecondaryButton } from "@/foundation/ui";
import { hasCode } from "@/foundation/platform-client";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { endPracticeSession, readPracticeSession } from "../api";
import { formatCountdown } from "../support/examTimers";

/** Declining ends the immediately paired room; the API has no pending match. */
export function MatchNotificationModal({ sessionId, onAccept, onDeclined }: {
  sessionId: string; onAccept: () => void; onDeclined: () => void;
}) {
  const acceptedKey = `peer_match_accepted_${sessionId}`;
  const callbacks = useRef({ onAccept, onDeclined });
  useEffect(() => { callbacks.current = { onAccept, onDeclined }; }, [onAccept, onDeclined]);
  const [deadline] = useState(() => {
    const key = `peer_match_deadline_${sessionId}`;
    try {
      const existing = Number(localStorage.getItem(key));
      if (existing > 0) return existing;
      const next = Date.now() + 120_000;
      localStorage.setItem(key, String(next));
      return next;
    } catch { return Date.now() + 120_000; }
  });
  const [now, setNow] = useState(Date.now);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const [expired, setExpired] = useState(false);
  const loaded = useAsync((signal) => readPracticeSession(sessionId, signal), [sessionId]);
  const ended = loaded.data?.status === "ended";
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    if ("Notification" in window && Notification.permission === "granted") {
      const notification = new Notification("Practice partner found", { body: "Your partner is ready. Accept your match within 2 minutes.", tag: sessionId });
      notification.onclick = () => { window.focus(); notification.close(); };
    }
    return () => window.clearInterval(timer);
  }, [sessionId]);
  useEffect(() => {
    const syncAcceptance = () => {
      try { if (localStorage.getItem(acceptedKey)) callbacks.current.onAccept(); } catch { /* Storage is optional. */ }
    };
    syncAcceptance();
    window.addEventListener("storage", syncAcceptance);
    return () => window.removeEventListener("storage", syncAcceptance);
  }, [acceptedKey]);
  const accept = () => {
    try { localStorage.setItem(acceptedKey, "accepted"); } catch { /* Storage is optional. */ }
    onAccept();
  };
  useEffect(() => {
    const timer = window.setInterval(loaded.reload, 10_000);
    return () => window.clearInterval(timer);
  }, [loaded.reload]);
  const declining = useRef(false);
  const decline = useCallback(async () => {
    if (declining.current) return;
    declining.current = true;
    setBusy(true); setFailure(null);
    try { await endPracticeSession(sessionId, "match_declined"); callbacks.current.onDeclined(); }
    catch (cause) {
      if (hasCode(cause, "practice_session_ended")) callbacks.current.onDeclined();
      else setFailure(cause);
    }
    finally { setBusy(false); declining.current = false; }
  }, [sessionId]);
  useEffect(() => {
    if (ended) return;
    const timer = window.setTimeout(() => {
      try { if (localStorage.getItem(acceptedKey)) return; } catch { /* Storage is optional. */ }
      setExpired(true);
      void decline();
    }, Math.max(0, deadline - Date.now()));
    return () => window.clearTimeout(timer);
  }, [deadline, ended, acceptedKey, decline]);
  return <Modal width="min(95vw, 480px)" height="fit-content" title="Practice partner found" hideCloseButton closeOnEscape={false} closeOnBackdrop={false} closeOnBack={false}>
    <ModalContent>
      <ModalLead title={ended ? "Partner unavailable" : expired ? "Match expired" : "Practice partner found!"}
        description={ended ? "Your practice partner is no longer available. Join the queue again to find someone else." : "A colleague is ready to practise with you. Would you like to accept?"} />
      {!ended && <p className="text-center font-mono text-2xl" role="timer">{formatCountdown(Math.max(0, Math.ceil((deadline - now) / 1000)))}</p>}
      {(failure || loaded.error) && <Alert tone="danger">{errorMessage(failure || loaded.error)}</Alert>}
      <ModalFooterActions>
        {ended ? <ModalPrimaryButton onClick={onDeclined}>Back to practice</ModalPrimaryButton> : <>
          <ModalSecondaryButton disabled={busy} onClick={() => void decline()}>{expired ? "Close match" : "Not now"}</ModalSecondaryButton>
          <ModalPrimaryButton disabled={busy || expired || loaded.loading || Boolean(loaded.error)} onClick={accept}>Accept</ModalPrimaryButton>
        </>}
      </ModalFooterActions>
    </ModalContent>
  </Modal>;
}
