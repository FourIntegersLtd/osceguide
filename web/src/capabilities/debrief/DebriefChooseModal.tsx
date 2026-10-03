"use client";

import { useState, type ReactNode } from "react";
import { HiChatAlt2, HiMicrophone, HiUser } from "react-icons/hi";
import { HiOutlineArrowLeft, HiOutlinePlay } from "react-icons/hi2";
import {
  Button,
  cn,
  Modal,
  ModalContent,
  ModalHelper,
  ModalIconWell,
  ModalTitle,
} from "@/foundation/ui";
import { DebriefSession } from "@/capabilities/debrief/DebriefSession";
import { PatientPracticePanel } from "@/capabilities/debrief/PatientPracticePanel";
import type { AttemptBrief, AttemptReview } from "@/capabilities/attempt-runner";
import { useCurrentExam, offersPatientPractice } from "@/foundation/session";
import { b2cCard } from "@/foundation/ui/productTokens";

type Service = "debrief" | "doctor" | null;

/**
 * Retiring client's `DebriefSessionModal` — choose debrief or practice-as-patient.
 */
export function DebriefChooseModal({
  examCode,
  setId,
  entryId,
  attemptId,
  brief,
  review,
  onClose,
  onDebriefEnded,
}: {
  examCode: string;
  setId: string | null;
  entryId: string | null;
  attemptId: string;
  brief: AttemptBrief | null;
  review: AttemptReview | null;
  onClose: () => void;
  /** The debrief attempt that has just ended, so the screen behind can wait for its summary. */
  onDebriefEnded?: (debriefAttemptId: string) => void;
}) {
  const { settings } = useCurrentExam();
  const sessionModes = settings.session_modes ?? ["debrief", "practice_as_patient"];
  const [active, setActive] = useState<Service>(null);
  const showPatientPractice = offersPatientPractice(settings);

  const handleClose = () => {
    setActive(null);
    onClose();
  };


  return (
    <Modal width="min(1100px, 95vw)" height="fit-content" onClose={handleClose} closeBarClassName="border-b-0 pb-0">
      <ModalContent className="flex flex-col space-y-3">
        {active ? (
          <div className="flex items-center justify-between gap-2 pb-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setActive(null);
              }}
              className="gap-1.5"
            >
              <HiOutlineArrowLeft className="h-3 w-3" aria-hidden />
              <span>Back</span>
            </Button>
          </div>
        ) : null}

        {!active ? (
          <div className="w-full">
            <ModalTitle>Choose your session</ModalTitle>
            <ModalHelper className="max-w-md">
              Select how you want to work with Athena on this station.
            </ModalHelper>
            <div className={cn("mt-4 grid grid-cols-1 gap-3", sessionModes.length > 1 && "md:grid-cols-2")}>
              {sessionModes.includes("debrief") ? (
                <ModeCard
                  icon={<HiChatAlt2 className="h-4 w-4" aria-hidden />}
                  title="Debrief session"
                  description="Review your consultation with Athena and get detailed feedback on your performance."
                  action={
                    <Button type="button" size="sm" onClick={() => setActive("debrief")} className="gap-1.5">
                      <HiMicrophone className="h-4 w-4" aria-hidden />
                      <span>Start debrief</span>
                    </Button>
                  }
                />
              ) : null}
              {showPatientPractice ? (
                <ModeCard
                  icon={<HiUser className="h-4 w-4" aria-hidden />}
                  title="Practice as patient"
                  description="Experience the ideal consultation from the patient's side, with Athena as your doctor."
                  action={
                    <Button type="button" variant="secondary" size="sm" onClick={() => setActive("doctor")} className="gap-1.5">
                      <HiOutlinePlay className="h-4 w-4" aria-hidden />
                      <span>Start</span>
                    </Button>
                  }
                />
              ) : null}
            </div>
          </div>
        ) : active === "debrief" ? (
          <div className="h-[min(620px,calc(90dvh-11rem))] min-h-0 overflow-hidden">
            <DebriefSession setId={setId} entryId={entryId} sourceAttemptId={attemptId}
              onEnded={onDebriefEnded} onDone={handleClose} />
          </div>
        ) : (
          <PatientPracticePanel attemptId={attemptId} examCode={examCode} brief={brief} review={review} />
        )}
      </ModalContent>
    </Modal>
  );
}

function ModeCard({ icon, title, description, action }: {
  icon: ReactNode;
  title: string;
  description: string;
  action: ReactNode;
}) {
  return (
    <section className={cn(b2cCard, "flex flex-col p-5")}>
      <ModalIconWell>{icon}</ModalIconWell>
      <h3 className="mt-3 text-osce-subheading font-semibold text-osce-ink-900">{title}</h3>
      <p className="mt-1 flex-1 text-osce-meta leading-relaxed text-b2c-text-muted">{description}</p>
      <div className="mt-4">{action}</div>
    </section>
  );
}
