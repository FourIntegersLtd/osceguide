"use client";

import {
  HiOutlineArrowRight,
  HiOutlineCheckCircle,
  HiOutlineClock,
} from "react-icons/hi2";
import {
  Modal,
  ModalContent,
  ModalFooterActions,
  ModalLead,
  ModalPrimaryButton,
} from "@/foundation/ui";

/**
 * Shown when the consultation timer ends during a mock — the retiring client's
 * `SimulationTimeUpModal`. Last station sends the candidate to complete the
 * session; otherwise they move on to the next station.
 */
export function SimulationTimeUpModal({
  isOpen,
  isLastStation,
  onNext,
}: {
  isOpen: boolean;
  isLastStation: boolean;
  onNext: () => void;
}) {
  if (!isOpen) return null;

  return (
    <Modal width="32rem" height="fit-content" hideCloseButton>
      <ModalContent>
        <ModalLead
          title="Time up"
          description={
            isLastStation
              ? "Your consultation time is over and the consultation has ended. Please complete the mock."
              : "Your consultation time is over and the consultation has ended. Please proceed to the next station."
          }
          icon={<HiOutlineClock aria-hidden />}
          iconTone="rose"
        />
        <ModalFooterActions>
          <ModalPrimaryButton onClick={onNext} className="gap-2">
            {isLastStation ? (
              <>
                <HiOutlineCheckCircle className="h-3.5 w-3.5" aria-hidden />
                Complete mock
              </>
            ) : (
              <>
                <HiOutlineArrowRight className="h-3.5 w-3.5" aria-hidden />
                Next station
              </>
            )}
          </ModalPrimaryButton>
        </ModalFooterActions>
      </ModalContent>
    </Modal>
  );
}
