"use client";

import {
  HiOutlineArrowPath,
  HiOutlineClock,
  HiOutlineExclamationTriangle,
  HiOutlineUsers,
  HiOutlineXMark,
} from "react-icons/hi2";
import { LuUserX } from "react-icons/lu";
import {
  Button,
  Modal,
  ModalCallout,
  ModalContent,
  ModalDangerButton,
  ModalFooterActions,
  ModalLead,
  ModalPrimaryButton,
  ModalSecondaryButton,
} from "@/foundation/ui";
import type { PartnerGone } from "../support/sessionState";

/*
 * The live-practice dialogs, in the retiring client's words and layout.
 * Each is a 500px fit-content modal unless the old one said otherwise.
 */

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
          description="We'll search for an available colleague for up to 10 minutes. You can get matched immediately and start a video session."
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

/** Shown straight after joining; closing it leaves the floating indicator. */
export function SearchingModal({
  onCancelSearch,
  onDismiss,
}: {
  onCancelSearch: () => void;
  onDismiss: () => void;
}) {
  return (
    <Modal width="500px" height="fit-content" onClose={onDismiss}>
      <ModalContent>
        <ModalLead
          title="Searching for a practice partner"
          description={
            <>
              We&apos;re looking for an available colleague to match you with.
              We&apos;ll search for up to 10 minutes. You can close this and
              continue browsing. We&apos;ll notify you when a match is found.
            </>
          }
          icon={<HiOutlineArrowPath className="h-4 w-4 animate-spin" />}
        />
        <ModalFooterActions>
          <ModalDangerButton onClick={onCancelSearch}>Cancel search</ModalDangerButton>
        </ModalFooterActions>
      </ModalContent>
    </Modal>
  );
}

export function QueueExpiredModal({ onClose }: { onClose: () => void }) {
  return (
    <Modal width="500px" height="fit-content" onClose={onClose}>
      <ModalContent>
        <ModalLead
          title="No Match Found"
          description="No practice partner found within 10 minutes. Try again or use AI practice."
          icon={<HiOutlineClock className="h-4 w-4" />}
          iconTone="orange"
        />
        <ModalCallout>
          <span className="inline-flex items-start gap-2">
            <HiOutlineUsers className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              <strong className="font-semibold">Want to try again?</strong> Click the
              &quot;Practice with colleague&quot; button again to rejoin the queue. You can
              also practice with our AI assistant while waiting for human partners.
            </span>
          </span>
        </ModalCallout>
        <ModalFooterActions>
          <ModalSecondaryButton onClick={onClose} className="w-full sm:w-auto">
            Close
          </ModalSecondaryButton>
        </ModalFooterActions>
      </ModalContent>
    </Modal>
  );
}

export const PARTNER_UNAVAILABLE_MESSAGE =
  "This practice session is no longer available. Someone else may have already joined.";

export function PartnerUnavailableModal({
  message = PARTNER_UNAVAILABLE_MESSAGE,
  onClose,
}: {
  message?: string;
  onClose: () => void;
}) {
  return (
    <Modal width="500px" height="fit-content" onClose={onClose}>
      <ModalContent>
        <ModalLead
          title="Session no longer available"
          description={<>{message}</>}
          icon={<LuUserX className="h-4 w-4" />}
          iconTone="orange"
        />
        <ModalFooterActions>
          <ModalPrimaryButton onClick={onClose} className="w-full sm:w-auto">
            OK
          </ModalPrimaryButton>
        </ModalFooterActions>
      </ModalContent>
    </Modal>
  );
}

/**
 * The partner never answered the match, or left the session early. Both offer
 * to requeue, which is what "Yes, Requeue Me" does. It cannot be dismissed:
 * the person has to choose.
 */
export function PartnerLeftModal({
  reason,
  isRequeuing,
  onRequeue,
  onGoToDashboard,
}: {
  reason: PartnerGone;
  isRequeuing: boolean;
  onRequeue?: () => void;
  onGoToDashboard: () => void;
}) {
  const noResponse = reason === "no_response";
  return (
    <Modal width="500px" height="fit-content" hideCloseButton closeOnBackdrop={false} closeOnEscape={false} closeOnBack={false}>
      <ModalContent>
        <ModalLead
          title={noResponse ? "Partner Didn't Respond" : "Partner Left"}
          description={
            noResponse
              ? "Your practice partner didn't respond to the match in time."
              : "Your practice partner has left the session."
          }
          icon={<HiOutlineExclamationTriangle className="h-4 w-4" />}
          iconTone="amber"
        />
        <ModalCallout className="border-osce-warning-border bg-osce-warning-bg/60">
          <span className="inline-flex items-start gap-2 text-osce-warning-text">
            <HiOutlineUsers className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              <strong className="font-semibold">Would you like to be requeued?</strong>{" "}
              We can find you a new practice partner right away, or you can return to the
              dashboard.
            </span>
          </span>
        </ModalCallout>
        <ModalFooterActions>
          {onRequeue && (
            <ModalPrimaryButton onClick={onRequeue} disabled={isRequeuing} className="w-full gap-2 sm:w-auto">
              {isRequeuing ? (
                <>
                  <HiOutlineArrowPath className="h-3.5 w-3.5 animate-spin" />
                  Requeuing...
                </>
              ) : (
                "Yes, Requeue Me"
              )}
            </ModalPrimaryButton>
          )}
          <ModalSecondaryButton onClick={onGoToDashboard} disabled={isRequeuing} className="w-full sm:w-auto">
            No, Go to Dashboard
          </ModalSecondaryButton>
        </ModalFooterActions>
      </ModalContent>
    </Modal>
  );
}

/** The floating card that keeps watching once the searching modal is closed. */
export function QueueIndicator({
  onCancel,
  onDismiss,
}: {
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
          <p className="text-osce-body font-semibold text-osce-ink-900">Finding a practice partner</p>
          <p className="mt-0.5 text-osce-caption text-osce-accent sm:text-osce-body">
            We&apos;ll notify you when matched
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
