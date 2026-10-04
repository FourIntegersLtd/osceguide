"use client";

import type { ReactNode } from "react";
import {
  Alert,
  Modal,
  ModalCommitButton,
  ModalContent,
  ModalDangerButton,
  ModalFooterActions,
  ModalSecondaryButton,
  ModalTitle,
  b2bTokens,
} from "@/foundation/ui";

/**
 * The chrome the team and the roster share.
 *
 * They were one screen in the retiring client — `/team` held a Members tab
 * with both staff and trainees on it — and they are two screens here. What
 * they still have in common is this: the tab strip under the page title, the
 * grouped card, and one dialog shape. It lives with Team because that is where
 * `TeamPageHeaderNav` and `TeamPageCard` came from.
 */

export interface Tab<T extends string> {
  key: T;
  label: string;
  /** A count shown beside the label, in grey. */
  count?: number;
}

/**
 * The segmented control under the page title.
 *
 * `/team`, `/team/activity` and `/team/onboard` were separate pages whose
 * every visit refetched the same two lists. There is one route per screen in
 * this client, so the sections are state, which also means switching tabs no
 * longer loses a half-typed invitation.
 */
export function TabStrip<T extends string>({
  tabs,
  active,
  onSelect,
  label,
}: {
  tabs: readonly Tab<T>[];
  active: T;
  onSelect: (key: T) => void;
  label: string;
}) {
  return (
    <div className={b2bTokens.b2bSegmentedControl} role="tablist" aria-label={label}>
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          role="tab"
          aria-selected={active === tab.key}
          onClick={() => onSelect(tab.key)}
          className={
            active === tab.key ? b2bTokens.b2bSegmentedTabActive : b2bTokens.b2bSegmentedTabInactive
          }
        >
          {tab.label}
          {tab.count !== undefined ? (
            <span className="text-osce-meta text-b2b-mid">{tab.count}</span>
          ) : null}
        </button>
      ))}
    </div>
  );
}

/** One dialog shape: title, body, inline failure, Cancel and a commit. */
export function Dialog({
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
    <Modal onClose={busy ? undefined : onClose} title={title} width="38rem">
      <ModalContent>
        <ModalTitle>{title}</ModalTitle>
        {lead ? <p className="mt-1 text-osce-body text-b2b-mid">{lead}</p> : null}
        {children ? <div className="mt-4 space-y-4">{children}</div> : null}
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

/** "3 Sept 2026, 14:20" — the audit log's stamp, and the entitlement's. */
export function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "None";
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
