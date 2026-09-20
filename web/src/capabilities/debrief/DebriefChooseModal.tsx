"use client";

import { useState } from "react";
import { HiChatAlt2, HiInformationCircle, HiUser } from "react-icons/hi";
import { HiOutlineArrowLeft, HiOutlineChevronRight } from "react-icons/hi2";
import {
  Button,
  Modal,
  ModalContent,
  ModalHelper,
  ModalIconWell,
  ModalTitle,
} from "@/foundation/ui";
import { DebriefSession } from "@/capabilities/debrief/DebriefSession";
import { DebriefSuggestedPrompts } from "@/capabilities/debrief/DebriefInformation";
import { PatientPracticePanel } from "@/capabilities/debrief/PatientPracticePanel";
import type { AttemptBrief, AttemptReview } from "@/capabilities/attempt-runner";

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
}: {
  examCode: string;
  setId: string | null;
  entryId: string | null;
  attemptId: string;
  brief: AttemptBrief | null;
  review: AttemptReview | null;
  onClose: () => void;
}) {
  const [active, setActive] = useState<Service>(null);
  const [showTips, setShowTips] = useState(false);
  const showPatientPractice = examCode.toLowerCase() !== "ortho";

  const handleClose = () => {
    setActive(null);
    setShowTips(false);
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
                setShowTips(false);
              }}
              className="gap-1.5"
            >
              <HiOutlineArrowLeft className="h-3 w-3" aria-hidden />
              <span>Back</span>
            </Button>
            {active === "debrief" ? (
              <Button
                type="button"
                variant={showTips ? "primary" : "ghost"}
                size="sm"
                onClick={() => setShowTips((value) => !value)}
                className="gap-1.5"
              >
                <HiInformationCircle className="h-4 w-4" aria-hidden />
                <span className="hidden sm:inline">Tips</span>
              </Button>
            ) : null}
          </div>
        ) : null}

        {showTips && active === "debrief" ? (
          <div className="overflow-hidden rounded-lg border border-b2c-border bg-b2c-surface-muted/50 p-3">
            <DebriefSuggestedPrompts examCode={examCode} />
          </div>
        ) : null}

        {!active ? (
          <div className="mx-auto w-full">
            <div className="mb-1 text-center">
              <ModalTitle>Choose Your Session</ModalTitle>
              <ModalHelper className="mx-auto max-w-md">
                Select how you want to interact with Athena to improve your consultation skills.
              </ModalHelper>
            </div>
            <div
              className={
                examCode === "ortho"
                  ? "mx-auto mt-4 max-w-md"
                  : "mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2"
              }
            >
              <button
                type="button"
                onClick={() => setActive("debrief")}
                className="flex w-full items-start gap-3 rounded-xl border border-b2c-border bg-osce-surface px-4 py-4 text-left transition hover:border-osce-accent/30 hover:bg-b2c-surface-muted active:scale-[0.99]"
              >
                <ModalIconWell>
                  <HiChatAlt2 className="h-4 w-4" aria-hidden />
                </ModalIconWell>
                <span className="min-w-0 flex-1">
                  <span className="block text-osce-body font-medium text-osce-ink-900">
                    Debrief Session
                  </span>
                  <span className="mt-0.5 block text-osce-body leading-relaxed text-b2c-text-muted">
                    Review your consultation with Athena and get detailed feedback on your
                    performance.
                  </span>
                </span>
                <HiOutlineChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-b2c-text-muted" />
              </button>
              {showPatientPractice ? (
                <button
                  type="button"
                  onClick={() => setActive("doctor")}
                  className="flex w-full items-start gap-3 rounded-xl border border-b2c-border bg-osce-surface px-4 py-4 text-left transition hover:border-osce-accent/30 hover:bg-b2c-surface-muted active:scale-[0.99]"
                >
                  <ModalIconWell>
                    <HiUser className="h-4 w-4" aria-hidden />
                  </ModalIconWell>
                  <span className="min-w-0 flex-1">
                    <span className="block text-osce-body font-medium text-osce-ink-900">
                      Practice as Patient
                    </span>
                    <span className="mt-0.5 block text-osce-body leading-relaxed text-b2c-text-muted">
                      Experience the ideal consultation from the patient&apos;s perspective with
                      Athena as your doctor.
                    </span>
                  </span>
                  <HiOutlineChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-b2c-text-muted" />
                </button>
              ) : null}
            </div>
          </div>
        ) : active === "debrief" ? (
          <div className="h-[min(620px,calc(90dvh-11rem))] min-h-0 overflow-hidden">
            <DebriefSession setId={setId} entryId={entryId} sourceAttemptId={attemptId} />
          </div>
        ) : (
          <PatientPracticePanel attemptId={attemptId} examCode={examCode} brief={brief} review={review} />
        )}
      </ModalContent>
    </Modal>
  );
}
