"use client";

import { HiOutlineVideoCamera } from "react-icons/hi2";
import {
  Alert,
  Modal,
  ModalCallout,
  ModalContent,
  ModalFooterActions,
  ModalLead,
  ModalPrimaryButton,
  ModalSecondaryButton,
} from "@/foundation/ui";
import type { PeerSession } from "@/capabilities/peer-practice/api";
import { longDate, meridiemTime } from "@/capabilities/peer-practice/support/time";

export function JoinablePeerSessionModal({
  session,
  isJoining,
  joinError,
  onJoin,
  onDismiss,
}: {
  session: PeerSession;
  isJoining?: boolean;
  joinError?: string | null;
  onJoin: () => void;
  onDismiss: () => void;
}) {
  const partner = session.partner_username ? `@${session.partner_username}` : "your partner";
  const active = session.status === "active";

  return (
    <Modal onClose={onDismiss} width="min(95vw, 440px)" height="fit-content">
      <ModalContent>
        <ModalLead
          title={active ? "Session in progress" : "Your session is ready"}
          description={`You have a session with ${partner} on ${longDate(session.starts_at)} at ${meridiemTime(session.starts_at)}.`}
          icon={<HiOutlineVideoCamera className="h-4 w-4" />}
        />
        <ModalCallout>
          {active ? "Rejoin the call to continue practising." : "You can join now — head to the call when you are ready."}
        </ModalCallout>
        {joinError && <Alert tone="danger" className="mt-3">{joinError}</Alert>}
        <ModalFooterActions>
          <ModalSecondaryButton onClick={onDismiss}>Not now</ModalSecondaryButton>
          <ModalPrimaryButton onClick={onJoin} disabled={isJoining}>
            {isJoining ? "Joining…" : active ? "Rejoin session" : "Join session"}
          </ModalPrimaryButton>
        </ModalFooterActions>
      </ModalContent>
    </Modal>
  );
}
