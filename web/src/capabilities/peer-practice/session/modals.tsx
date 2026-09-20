"use client";

import { useEffect, useRef, useState } from "react";
import { Modal, ModalContent, ModalLead, ModalFooterActions, ModalPrimaryButton } from "@/foundation/ui";
import type { RunnerPhase } from "../support/sessionState";

export function PhaseModals({ phase, remaining, preparationStarted }: {
  phase: RunnerPhase; remaining: number | null; preparationStarted: string | null | undefined;
}) {
  const [warning, setWarning] = useState(false);
  const [timeUp, setTimeUp] = useState(false);
  const warned = useRef(false);
  const previous = useRef(phase);
  useEffect(() => {
    if (phase === "consultation" && remaining !== null && remaining > 0 && remaining <= 360 && !warned.current) {
      warned.current = true; setWarning(true);
    }
    if (previous.current === "consultation" && phase === "debrief") { setWarning(false); setTimeUp(true); }
    previous.current = phase;
  }, [phase, remaining]);
  useEffect(() => {
    if (!preparationStarted) return;
    const audio = new Audio("/sounds/partner-joined.mp3");
    void audio.play().catch(() => {});
    return () => audio.pause();
  }, [preparationStarted]);
  useEffect(() => {
    if (!timeUp) return;
    const audio = new Audio("/sounds/alarm.mp3"); audio.loop = true;
    void audio.play().catch(() => {});
    return () => { audio.pause(); audio.currentTime = 0; };
  }, [timeUp]);
  const showingWarning = warning && phase === "consultation";
  const showingTimeUp = timeUp && phase === "debrief";
  if (!showingWarning && !showingTimeUp) return null;
  const close = () => { setWarning(false); setTimeUp(false); };
  return <Modal onClose={close} width="min(95vw, 440px)" height="fit-content">
    <ModalContent>
      <ModalLead title={showingTimeUp ? "Time's up" : "Time Warning"}
        description={showingTimeUp ? "Consultation has ended. Please begin the debrief with your partner." : "6 minutes remaining! Please prepare to move to management."} />
      <ModalFooterActions><ModalPrimaryButton onClick={close}>{showingTimeUp ? "Begin debrief" : "Got it"}</ModalPrimaryButton></ModalFooterActions>
    </ModalContent>
  </Modal>;
}
