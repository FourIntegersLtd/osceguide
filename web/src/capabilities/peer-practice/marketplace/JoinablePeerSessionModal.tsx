"use client";

import { HiOutlineVideoCamera } from "react-icons/hi2";
import Alert from "@/foundation/forms/Alert";
import {
  Modal,
  ModalCallout,
  ModalContent,
  ModalFooterActions,
  ModalLead,
  ModalPrimaryButton,
  ModalSecondaryButton,
  Spinner,
} from "@/foundation/ui";
import type { PeerSession } from "@/capabilities/peer-practice/api";
import { longDate, meridiemTime } from "@/capabilities/peer-practice/support/time";

/** "Your session is ready!" — raised anywhere once an arranged session opens. */
export function JoinablePeerSessionModal({
  session,
  isJoining = false,
  joinError = null,
  onJoin,
  onDismiss,
}: {
  session: PeerSession;
  isJoining?: boolean;
  joinError?: string | null;
  onJoin: () => void;
  onDismiss: () => void;
}) {
  const partner = session.partner_username || "your partner";
  const isActive = session.status === "active";

  return (
    <Modal width="500px" height="fit-content" onClose={onDismiss}>
      <ModalContent>
        <ModalLead
          title={<>{isActive ? "Session in progress" : "Your session is ready!"}</>}
          description={
            <>
              You have a marketplace session with{" "}
              <span className="font-medium text-osce-ink-900">@{partner}</span> on{" "}
              {longDate(session.starts_at)} at {meridiemTime(session.starts_at)}.
            </>
          }
          icon={<HiOutlineVideoCamera className="h-4 w-4" />}
        />

        <ModalCallout>
          <strong className="font-semibold">
            {isActive ? "Rejoin the session" : "You can join now"}
          </strong>{" "}
          . head to the call and start practicing.
        </ModalCallout>

        {joinError ? <Alert message={joinError} type="error" className="mt-4" /> : null}

        <ModalFooterActions className="flex-col sm:flex-row">
          <ModalSecondaryButton onClick={onDismiss} disabled={isJoining} className="w-full sm:flex-1">
            Later
          </ModalSecondaryButton>
          <ModalPrimaryButton onClick={onJoin} disabled={isJoining} className="w-full gap-2 sm:flex-1">
            {isJoining ? (
              <>
                <Spinner size="xs" className="text-current" label="Joining" />
                Joining...
              </>
            ) : isActive ? (
              "Rejoin session"
            ) : (
              "Join session"
            )}
          </ModalPrimaryButton>
        </ModalFooterActions>

        <p className="mt-3 text-center text-osce-meta text-osce-ink-500">
          To join later, go to{" "}
          <span className="font-medium text-osce-ink-900">Marketplace, Upcoming sessions</span>{" "}
          tab
        </p>
      </ModalContent>
    </Modal>
  );
}
