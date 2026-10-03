"use client";

import { useEffect, useRef, useState } from "react";
import { IoTimeOutline } from "react-icons/io5";
import { Modal, ModalContent, ModalFooterActions, ModalLead, ModalPrimaryButton } from "@/foundation/ui";
import type { RunnerPhase } from "../support/sessionState";

/** Seconds left in the consultation when the "6 minutes remaining" warning rings. */
const WARNING_AT_SECONDS = 360;

/**
 * The two timing prompts: six minutes left in the consultation, and the move
 * to the debrief. Both follow the server's phase, never a browser countdown;
 * the second plays the alarm until it is dismissed. The partner-joined chime
 * plays once when the preparation clock starts.
 */
export function PhaseModals({
  phase,
  remaining,
  preparationStarted,
}: {
  phase: RunnerPhase;
  remaining: number | null;
  preparationStarted: string | null | undefined;
}) {
  const [warning, setWarning] = useState(false);
  const [timeUp, setTimeUp] = useState(false);
  const warned = useRef(false);
  const previous = useRef(phase);

  useEffect(() => {
    if (phase === "consultation" && remaining !== null && remaining > 0 && remaining <= WARNING_AT_SECONDS && !warned.current) {
      warned.current = true;
      setWarning(true);
    }
    if (previous.current === "consultation" && phase === "debrief") {
      setWarning(false);
      setTimeUp(true);
    }
    previous.current = phase;
  }, [phase, remaining]);

  useEffect(() => {
    if (!preparationStarted) return;
    const audio = new Audio("/sounds/partner-joined.mp3");
    void audio.play().catch(() => undefined);
    return () => audio.pause();
  }, [preparationStarted]);

  useEffect(() => {
    if (!timeUp) return;
    const audio = new Audio("/sounds/alarm.mp3");
    audio.loop = true;
    void audio.play().catch(() => undefined);
    return () => {
      audio.pause();
      audio.currentTime = 0;
    };
  }, [timeUp]);

  if (warning && phase === "consultation") {
    return (
      <Modal width="500px" height="fit-content" onClose={() => setWarning(false)}>
        <ModalContent>
          <ModalLead
            title="Time warning"
            description="6 minutes remaining! Please prepare to move to management."
            icon={<IoTimeOutline className="h-4 w-4" aria-hidden />}
            iconTone="amber"
          />
          <ModalFooterActions>
            <ModalPrimaryButton onClick={() => setWarning(false)} className="w-full sm:w-auto">
              Got it
            </ModalPrimaryButton>
          </ModalFooterActions>
        </ModalContent>
      </Modal>
    );
  }

  if (timeUp && phase === "debrief") {
    return (
      <Modal width="500px" height="fit-content" onClose={() => setTimeUp(false)}>
        <ModalContent>
          <ModalLead
            title="Time's up"
            description="Consultation has ended. Please begin the debrief with your partner."
            icon={<IoTimeOutline className="h-4 w-4" aria-hidden />}
            iconTone="amber"
          />
          <ModalFooterActions>
            <ModalPrimaryButton onClick={() => setTimeUp(false)} className="w-full sm:w-auto">
              Begin debrief
            </ModalPrimaryButton>
          </ModalFooterActions>
        </ModalContent>
      </Modal>
    );
  }

  return null;
}
