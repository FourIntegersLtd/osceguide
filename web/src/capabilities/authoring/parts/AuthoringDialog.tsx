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
import { boardMeta } from "@/capabilities/authoring/parts/boardUi";
import { boardBtn } from "@/foundation/ui/boardKit";

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
  after,
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
  /** Content below the footer buttons, still inside the dialog (e.g. a list of recent work). */
  after?: ReactNode;
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
    surface === "platform" ? "text-ink-subtle" : "text-ink-muted";

  /** The staff console keeps its tighter dialog; assess, hire and partner use the roomy rhythm. */
  const roomy = surface !== "platform";

  if (roomy) {
    /* The board's .dlg: 520px, radius 14, padding 24, no icon; Modal still owns the focus trap and scroll lock. */
    return (
      <Modal
        onClose={busy ? undefined : onClose}
        title={title}
        /* The board's .dlg is content-box: 520px plus 24px padding each side. */
        width={width === "42rem" ? "35.5rem" : width}
        hideCloseButton
        variant="board"
      >
        <div className="flex flex-col gap-[15px]">
          <h2 className="m-0 text-assess-desc font-semibold !leading-[normal] text-ink">{title}</h2>
          {lead ? <div className={`${boardMeta} !text-assess-label !leading-[1.5]`}>{lead}</div> : null}
          {children ? <div className="flex flex-col gap-4">{children}</div> : null}
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <div className="flex flex-wrap items-center justify-end gap-[10px]">
            <button type="button" className={boardBtn()} onClick={onClose} disabled={busy}>
              Cancel
            </button>
            <button
              type="button"
              className={boardBtn(tone === "danger" ? "danger" : "primary")}
              onClick={onCommit}
              disabled={busy || commitDisabled}
            >
              {busy ? busyLabel : commitLabel}
            </button>
          </div>
          {after}
        </div>
      </Modal>
    );
  }

  return (
    <Modal onClose={busy ? undefined : onClose} title={title} width={width}>
      <ModalContent>
        <ModalTitle>{title}</ModalTitle>
        {lead ? <p className={`${roomy ? "mt-2" : "mt-1"} text-osce-body ${leadClass}`}>{lead}</p> : null}
        <div className={roomy ? "mt-6 space-y-6" : "mt-4 space-y-4"}>{children}</div>
        {error ? (
          <Alert tone="danger" className={roomy ? "mt-6" : "mt-4"}>
            {error}
          </Alert>
        ) : null}
        <ModalFooterActions className={roomy ? "mt-8" : "mt-6"}>
          <ModalSecondaryButton onClick={onClose} disabled={busy}>
            Cancel
          </ModalSecondaryButton>
          <Commit onClick={onCommit} disabled={busy || commitDisabled}>
            {busy ? busyLabel : commitLabel}
          </Commit>
        </ModalFooterActions>
        {after ? <div className="mt-6">{after}</div> : null}
      </ModalContent>
    </Modal>
  );
}
