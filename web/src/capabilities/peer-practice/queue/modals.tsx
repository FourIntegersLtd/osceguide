"use client";

import {
  HiOutlineArrowPath,
  HiOutlineLightBulb,
  HiOutlineUsers,
  HiOutlineXMark,
} from "react-icons/hi2";
import {
  Button,
  Modal,
  ModalBody,
  ModalCallout,
  ModalContent,
  ModalFooterActions,
  ModalFootnote,
  ModalLead,
  ModalList,
  ModalListRow,
  ModalPrimaryButton,
  ModalSection,
  ModalSectionBullets,
  ModalSecondaryButton,
} from "@/foundation/ui";
import type { QueueStatus } from "@/capabilities/peer-practice/api";

/** The short "shall I start looking?" prompt behind the Live Practice button. */
export function LivePracticeModal({
  isOpen,
  onClose,
  onStartNow,
  isJoiningQueue,
}: {
  isOpen: boolean;
  onClose: () => void;
  onStartNow: () => void;
  isJoiningQueue: boolean;
}) {
  if (!isOpen) return null;
  return (
    <Modal
      width="min(95vw, 420px)"
      height="fit-content"
      onClose={() => !isJoiningQueue && onClose()}
    >
      <ModalContent>
        <ModalLead
          title="Live practice"
          description="We'll look for an available colleague. You can get matched immediately and start a video session."
          icon={<HiOutlineUsers className="h-4 w-4" />}
        />
        <ModalFooterActions>
          <ModalSecondaryButton onClick={onClose} disabled={isJoiningQueue}>
            Cancel
          </ModalSecondaryButton>
          <ModalPrimaryButton onClick={onStartNow} disabled={isJoiningQueue} className="gap-2">
            {isJoiningQueue ? (
              <>
                <HiOutlineArrowPath className="h-3.5 w-3.5 animate-spin" />
                Joining...
              </>
            ) : (
              <>
                <HiOutlineUsers className="h-3.5 w-3.5" />
                Join now
              </>
            )}
          </ModalPrimaryButton>
        </ModalFooterActions>
      </ModalContent>
    </Modal>
  );
}

/**
 * Waiting, with the place in the queue the backend actually knows.
 *
 * The retiring modal ran its own ten-minute countdown because the old backend
 * expired a queue entry and never said where anybody stood. This one shows the
 * two numbers the stream pushes — the position and how many are waiting — and
 * runs no clock, because there is no deadline to count towards.
 */
export function QueueWaitingModal({
  status,
  live,
  onCancel,
  onKeepWaiting,
}: {
  status: QueueStatus | null;
  live: boolean;
  onCancel: () => void;
  onKeepWaiting: () => void;
}) {
  const position = status?.position ?? null;

  return (
    <Modal width="500px" height="fit-content" title="Finding a practice partner" onClose={onKeepWaiting}>
      <ModalContent>
        <ModalLead
          title="Finding a practice partner"
          description="Looking for another user to practice with..."
          icon={<HiOutlineArrowPath className="h-4 w-4 animate-spin" />}
        />

        <ModalSection>
          <div className="text-osce-meta leading-relaxed text-b2c-text-secondary">
            <p>
              {position !== null ? (
                <>
                  You are <span className="font-semibold text-osce-ink-900">number {position}</span>{" "}
                  in the queue.
                </>
              ) : (
                "You are in the queue."
              )}{" "}
              <span className="font-semibold text-osce-ink-900">{status?.waiting_count ?? 0}</span>{" "}
              waiting for this exam.
            </p>
            <p className="mt-1">
              {live
                ? "You can close this and carry on; we'll let you know the moment someone joins."
                : "Reconnecting to the live updates — your place in the queue is safe."}
            </p>
          </div>
        </ModalSection>

        <ModalCallout>
          <span className="inline-flex items-start gap-2">
            <HiOutlineLightBulb className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              <strong className="font-semibold">Suggestion while you wait</strong>
              <br />
              Try AI practice to keep learning while we find you a human partner
            </span>
          </span>
        </ModalCallout>

        <ModalFooterActions className="flex-col md:flex-row">
          <ModalSecondaryButton onClick={onCancel} className="w-full whitespace-normal md:flex-1">
            Cancel &amp; Try AI Practice
          </ModalSecondaryButton>
          <ModalPrimaryButton onClick={onKeepWaiting} className="w-full whitespace-normal md:flex-1">
            Keep waiting in the background
          </ModalPrimaryButton>
        </ModalFooterActions>
      </ModalContent>
    </Modal>
  );
}

/** The floating card that keeps watching once the modal is dismissed. */
export function QueueIndicator({
  waitingCount,
  onCancel,
  onDismiss,
}: {
  waitingCount: number;
  onCancel: () => void;
  onDismiss: () => void;
}) {
  return (
    <div className="fixed bottom-3 left-3 right-3 z-[9999] rounded-xl border border-osce-accent-subtle bg-osce-accent-muted p-3 text-osce-ink-900 sm:bottom-4 sm:left-auto sm:right-4 sm:max-w-sm sm:p-4">
      <button
        onClick={onDismiss}
        className="absolute -right-2 -top-2 flex h-7 w-7 items-center justify-center rounded-full border border-osce-accent-subtle bg-white text-osce-accent transition-colors hover:bg-osce-accent-muted hover:text-osce-accent-hover"
        aria-label="Dismiss"
      >
        <HiOutlineXMark className="h-3.5 w-3.5" />
      </button>
      <div className="flex items-center gap-3 sm:gap-4">
        <div className="relative flex-shrink-0">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-osce-accent-subtle sm:h-12 sm:w-12">
            <HiOutlineUsers className="h-4 w-4 text-osce-accent sm:h-5 sm:w-5" />
          </div>
          <div className="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-osce-accent sm:h-5 sm:w-5">
            <HiOutlineArrowPath className="h-2.5 w-2.5 animate-spin text-white sm:h-3 sm:w-3" />
          </div>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-osce-body font-semibold text-osce-ink-900">
            Finding a practice partner
          </p>
          <p className="mt-0.5 text-osce-caption text-osce-accent sm:text-osce-body">
            {waitingCount} waiting · we&apos;ll notify you when matched
          </p>
        </div>
        <Button
          type="button"
          variant="primary"
          size="sm"
          onClick={onCancel}
          className="shrink-0 sm:hidden"
          aria-label="Leave queue"
        >
          Leave
        </Button>
      </div>
      <Button
        type="button"
        variant="primary"
        size="md"
        fullWidth
        onClick={onCancel}
        className="mt-3 hidden gap-2 sm:flex"
        aria-label="Leave queue"
      >
        Leave Queue
      </Button>
    </div>
  );
}

/** The long-form explanation behind the (i) next to the practice button. */
export function PeerPracticeInfoModal({
  onStartPractice,
  isLoading,
  onClose,
}: {
  onStartPractice: () => void;
  isLoading: boolean;
  onClose: () => void;
}) {
  return (
    <Modal width="600px" height="fit-content" onClose={onClose}>
      <ModalBody>
        <ModalLead
          title="Practice with colleagues"
          description="Practice clinical scenarios with colleagues in real-time video consultations."
          icon={<HiOutlineUsers className="h-5 w-5" />}
        />

        <ModalSection
          title="How it works"
          icon={<HiOutlineUsers className="h-3.5 w-3.5" />}
          iconTone="emerald"
          tint="emerald"
        >
          <ModalList>
            <ModalListRow
              marker={<StepMarker>1</StepMarker>}
              title="Matching"
              description="When you start, you join a queue for your exam. We pair whoever has been waiting longest, so you are told where you stand while you wait."
            />
            <ModalListRow
              marker={<StepMarker>2</StepMarker>}
              title="Role assignment"
              description={
                <>
                  Your role (Doctor or Patient) is{" "}
                  <strong className="font-medium text-osce-ink-900">assigned automatically</strong>{" "}
                  from your practice history so opportunities stay balanced.
                </>
              }
            />
          </ModalList>
        </ModalSection>

        <ModalSection title="Session flow">
          <ModalSectionBullets
            items={[
              <>
                <strong className="font-medium text-osce-ink-900">Matching:</strong> You are put in
                a room together as soon as a partner is found
              </>,
              <>
                <strong className="font-medium text-osce-ink-900">Video:</strong> Allow your
                microphone · the consultation begins immediately
              </>,
              <>
                <strong className="font-medium text-osce-ink-900">Ending:</strong> Either of you can
                end the session when you are done
              </>,
            ]}
          />
        </ModalSection>

        <ModalFooterActions>
          <ModalPrimaryButton onClick={onStartPractice} disabled={isLoading} className="gap-2">
            <HiOutlineUsers className="h-3.5 w-3.5 shrink-0" />
            {isLoading ? "Starting..." : "Start practice session"}
          </ModalPrimaryButton>
        </ModalFooterActions>

        <ModalFootnote>
          You can leave the queue at any time before a match is confirmed.
        </ModalFootnote>
      </ModalBody>
    </Modal>
  );
}

function StepMarker({ children }: { children: React.ReactNode }) {
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-osce-accent-muted text-osce-caption font-semibold text-osce-accent">
      {children}
    </span>
  );
}
