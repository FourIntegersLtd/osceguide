"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { HiOutlineBell, HiOutlineExclamationTriangle } from "react-icons/hi2";
import {
  Modal,
  ModalCallout,
  ModalContent,
  ModalFooterActions,
  ModalLead,
  ModalPrimaryButton,
  ModalSecondaryButton,
  ModalSection,
} from "@/foundation/ui";
import { formatCountdown } from "../support/examTimers";

/** How long somebody has to answer a match, as the retiring modal counted it. */
export const MATCH_RESPONSE_SECONDS = 120;

/**
 * When the answer is due: the server's `accept_expires_at` once the session
 * has been read, which is the clock that actually times the match out. Until
 * then, a local two minutes that survives a reload, so refreshing the page
 * does not buy another two minutes.
 */
function responseDeadline(sessionId: string, expiresAt: string | null): number {
  const server = expiresAt ? Date.parse(expiresAt) : Number.NaN;
  if (Number.isFinite(server)) return server;
  const key = `peer_match_deadline_${sessionId}`;
  const fresh = Date.now() + MATCH_RESPONSE_SECONDS * 1000;
  try {
    const stored = Number(localStorage.getItem(key));
    if (stored > 0) return stored;
    localStorage.setItem(key, String(fresh));
  } catch {
    /* Storage is optional; the countdown still runs for this page. */
  }
  return fresh;
}

/**
 * "Practice partner found", with two minutes to answer. "Start Session" accepts
 * (the provider calls `/accept`); "Not Now" and running out of time decline.
 *
 * Closing it (the X or the backdrop) answers nothing, exactly as before: the
 * server's no-response timeout then tells the partner. Running out of time
 * declines and turns the modal into its "automatically declined" state.
 */
export function MatchNotificationModal({
  sessionId,
  expiresAt,
  isAccepting,
  onAccept,
  onDecline,
  onAutoDecline,
  onDismiss,
}: {
  sessionId: string;
  expiresAt: string | null;
  isAccepting: boolean;
  onAccept: () => void;
  onDecline: () => void;
  onAutoDecline: () => void;
  onDismiss: () => void;
}) {
  const deadline = useMemo(() => responseDeadline(sessionId, expiresAt), [sessionId, expiresAt]);
  const secondsLeft = () => Math.max(0, Math.floor((deadline - Date.now()) / 1000));
  const [timeLeft, setTimeLeft] = useState(secondsLeft);
  const [isExpired, setIsExpired] = useState(false);
  const autoDecline = useRef(onAutoDecline);
  useEffect(() => {
    autoDecline.current = onAutoDecline;
  }, [onAutoDecline]);

  useEffect(() => {
    if (isExpired) return undefined;
    const timer = window.setInterval(() => {
      const remaining = Math.max(0, Math.floor((deadline - Date.now()) / 1000));
      setTimeLeft(remaining);
      if (remaining <= 0) {
        setIsExpired(true);
        autoDecline.current();
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [deadline, isExpired]);

  return (
    <Modal width="500px" height="fit-content" onClose={onDismiss}>
      {isExpired ? (
        <ModalContent>
          <ModalLead
            title="Match automatically declined"
            description="You have been automatically declined because no response was received within the time limit."
            icon={<HiOutlineExclamationTriangle className="h-4 w-4" />}
            iconTone="orange"
          />
          <ModalCallout>
            <strong className="font-semibold">You can try again manually</strong> by clicking
            the practice button again.
          </ModalCallout>
          <ModalFooterActions>
            <ModalPrimaryButton onClick={onDismiss} className="w-full sm:w-auto">
              Close
            </ModalPrimaryButton>
          </ModalFooterActions>
        </ModalContent>
      ) : (
        <ModalContent>
          <ModalLead
            title="Practice partner found"
            description="A practice partner is available. Start your practice session now?"
            icon={<HiOutlineBell className="h-4 w-4" />}
          />
          <ModalSection tint="amber">
            <p className="text-osce-meta font-medium text-osce-warning-text" role="timer">
              Time to respond: {formatCountdown(timeLeft)}
            </p>
            <p className="mt-0.5 text-osce-meta leading-relaxed text-b2c-text-secondary">
              This match will automatically decline if no response is received.
            </p>
          </ModalSection>
          <ModalFooterActions>
            <ModalSecondaryButton onClick={onDecline} disabled={isAccepting} className="flex-1 sm:flex-none">
              Not Now
            </ModalSecondaryButton>
            <ModalPrimaryButton onClick={onAccept} disabled={isAccepting} aria-busy={isAccepting || undefined} className="flex-1 sm:flex-none">
              {isAccepting ? "Starting…" : "Start Session"}
            </ModalPrimaryButton>
          </ModalFooterActions>
        </ModalContent>
      )}
    </Modal>
  );
}
