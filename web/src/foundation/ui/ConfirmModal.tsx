"use client";

import React, { useId, useState } from "react";
import {
  HiOutlineExclamationTriangle,
  HiOutlineQuestionMarkCircle,
} from "react-icons/hi2";
import Modal from "@/foundation/ui/Modal";
import {
  ModalContent,
  ModalDangerButton,
  ModalFooterActions,
  ModalLead,
  ModalPrimaryButton,
  ModalSecondaryButton,
} from "@/foundation/ui/ModalContent";
import { B2CInlineError } from "@/foundation/ui/B2CErrorState";

export interface ConfirmModalProps {
  isOpen: boolean;
  onCancel: () => void;
  /** Return the promise and the confirm button says it is working until it settles. */
  onConfirm: () => unknown;
  message: string | React.ReactNode;
  title?: string;
  confirmText?: string;
  cancelText?: string;
  cancelButton?: boolean;
  /** `danger` renders the confirm button in the destructive style. */
  tone?: "default" | "danger";
  /** Disables both buttons and the backdrop while the action runs. */
  isLoading?: boolean;
  confirmDisabled?: boolean;
  /** Inline error shown above the actions (e.g. the action failed; try again). */
  error?: string | null;
  /** Optional extra content (e.g. a type-to-confirm input). */
  children?: React.ReactNode;
  /** When false, Back does not close the modal (avoids extra history entries). */
  closeOnBack?: boolean;
}

const ConfirmModal = ({
  isOpen,
  onCancel,
  onConfirm,
  message,
  title = "Confirm",
  confirmText = "Confirm",
  cancelText = "Cancel",
  cancelButton = true,
  tone = "default",
  isLoading = false,
  confirmDisabled = false,
  error,
  children,
  closeOnBack = true,
}: ConfirmModalProps) => {
  const titleId = useId();
  const [pending, setPending] = useState(false);
  /*
    The caller owns the error (usually an action hook's), so a failure from an earlier open would
    show again on the next one. The dialog drops whatever error was there when it opened, until
    the error clears (a new confirm clears it first) and a fresh one arrives.
  */
  const [wasOpen, setWasOpen] = useState(isOpen);
  const [stale, setStale] = useState<string | null>(isOpen ? (error ?? null) : null);
  if (isOpen !== wasOpen) {
    setWasOpen(isOpen);
    setStale(isOpen ? (error ?? null) : null);
  } else if (!error && stale) {
    setStale(null);
  }
  const shownError = error && error !== stale ? error : null;
  if (!isOpen) return null;

  const busy = isLoading || pending;
  const handleConfirm = () => {
    const result = onConfirm();
    if (result instanceof Promise) {
      setPending(true);
      void result.finally(() => setPending(false));
    }
  };

  const ConfirmButton =
    tone === "danger" ? ModalDangerButton : ModalPrimaryButton;
  const handleCancel = () => {
    if (!busy) onCancel();
  };

  return (
    <Modal
      onClose={handleCancel}
      width="28rem"
      height="fit-content"
      hideCloseButton
      labelledBy={titleId}
      closeOnBackdrop={!busy}
      closeOnEscape={!busy}
      closeOnBack={closeOnBack}
    >
      <ModalContent>
        <ModalLead
          id={titleId}
          title={title}
          description={message}
          icon={
            tone === "danger" ? (
              <HiOutlineExclamationTriangle className="h-5 w-5" />
            ) : (
              <HiOutlineQuestionMarkCircle className="h-5 w-5" />
            )
          }
          iconTone={tone === "danger" ? "rose" : "primary"}
        />
        {children}
        <B2CInlineError message={shownError} />
        <ModalFooterActions>
          {cancelButton ? (
            <ModalSecondaryButton onClick={handleCancel} disabled={busy}>
              {cancelText}
            </ModalSecondaryButton>
          ) : null}
          <ConfirmButton
            onClick={handleConfirm}
            disabled={busy || confirmDisabled}
            aria-busy={busy || undefined}
          >
            {busy ? "Working…" : confirmText}
          </ConfirmButton>
        </ModalFooterActions>
      </ModalContent>
    </Modal>
  );
};

export default ConfirmModal;