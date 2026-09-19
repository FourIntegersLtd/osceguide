"use client";

import type { ReactNode } from "react";
import {
  Alert,
  Modal,
  ModalContent,
  ModalCommitButton,
  ModalDangerButton,
  ModalFooterActions,
  ModalSecondaryButton,
  ModalTitle,
} from "@/foundation/ui";

/**
 * The one dialog shape authoring uses.
 *
 * Every authoring modal in the retiring client was a title, a body, an inline
 * error and a Cancel/commit footer — and each of the three trees had its own
 * copy, with three different paddings. One component, so a change to the
 * footer is a change everywhere.
 */
export function AuthoringDialog({
  open,
  title,
  lead,
  error,
  busy = false,
  commitLabel,
  busyLabel,
  commitDisabled = false,
  tone = "commit",
  onClose,
  onCommit,
  children,
}: {
  open: boolean;
  title: string;
  lead?: ReactNode;
  error?: string | null;
  busy?: boolean;
  commitLabel: string;
  busyLabel: string;
  commitDisabled?: boolean;
  tone?: "commit" | "danger";
  onClose: () => void;
  onCommit: () => void;
  children?: ReactNode;
}) {
  if (!open) return null;
  const Commit = tone === "danger" ? ModalDangerButton : ModalCommitButton;

  return (
    <Modal onClose={busy ? undefined : onClose} title={title} width="42rem">
      <ModalContent>
        <ModalTitle>{title}</ModalTitle>
        {lead ? <p className="mt-1 text-osce-body text-b2b-mid">{lead}</p> : null}
        <div className="mt-4 space-y-4">{children}</div>
        {error ? (
          <Alert tone="danger" className="mt-4">
            {error}
          </Alert>
        ) : null}
        <ModalFooterActions className="mt-6">
          <ModalSecondaryButton onClick={onClose} disabled={busy}>
            Cancel
          </ModalSecondaryButton>
          <Commit onClick={onCommit} disabled={busy || commitDisabled}>
            {busy ? busyLabel : commitLabel}
          </Commit>
        </ModalFooterActions>
      </ModalContent>
    </Modal>
  );
}
