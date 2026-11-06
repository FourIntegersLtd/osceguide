"use client";

import { ConfirmModal, type ConfirmModalProps } from "@/foundation/ui";
import { AuthoringDialog } from "@/capabilities/authoring/parts/AuthoringDialog";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";

/**
 * A yes/no box. Organisation arms get the board's plain dialog; the staff console keeps the
 * foundation confirm with its icon.
 */
export function AuthoringConfirm(props: ConfirmModalProps) {
  const chrome = useAuthoringChrome();
  if (chrome.b2c) return <ConfirmModal {...props} />;
  const { isOpen, onCancel, onConfirm, message, title = "Confirm", confirmText = "Confirm", tone, isLoading, error, children } = props;
  return (
    <AuthoringDialog
      open={isOpen}
      title={title}
      lead={message}
      error={error}
      busy={Boolean(isLoading)}
      commitLabel={confirmText}
      busyLabel="Working…"
      tone={tone === "danger" ? "danger" : "commit"}
      commitDisabled={props.confirmDisabled}
      onClose={onCancel}
      onCommit={() => void onConfirm()}
    >
      {children}
    </AuthoringDialog>
  );
}
