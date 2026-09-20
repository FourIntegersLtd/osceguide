"use client";

import type { ReactNode } from "react";
import {
  Alert,
  Modal,
  ModalCommitButton,
  ModalDangerButton,
  ModalFooterActions,
  ModalPrimaryButton,
  ModalSecondaryButton,
  ModalTitle,
  ModalContent,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities";

/**
 * The one dialog shape authoring uses.
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
  width = "42rem",
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
  width?: string;
}) {
  const { surface } = useSurface();

  if (!open) return null;

  const Commit =
    tone === "danger"
      ? ModalDangerButton
      : surface === "platform"
        ? ModalPrimaryButton
        : ModalCommitButton;
  const leadClass =
    surface === "platform" ? "text-b2c-text-muted" : "text-b2b-mid";

  return (
    <Modal onClose={busy ? undefined : onClose} title={title} width={width}>
      <ModalContent>
        <ModalTitle>{title}</ModalTitle>
        {lead ? <p className={`mt-1 text-osce-body ${leadClass}`}>{lead}</p> : null}
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
