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
  icon: (props: { className?: string; "aria-hidden"?: boolean }) => ReactNode;
}

/**
 * The tab strip that used to be three routes.
 *
 * `/team`, `/team/activity` and `/team/onboard` were separate pages whose
 * every visit refetched the same two lists. There is one route per screen in
 * this client, so the sections are state — which also means switching tabs no
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
    <nav className={b2bTokens.b2bTabStrip} aria-label={label}>
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          onClick={() => onSelect(tab.key)}
          className={
            active === tab.key
              ? b2bTokens.b2bWorkspaceTabActive
              : b2bTokens.b2bWorkspaceTabInactive
          }
          aria-current={active === tab.key ? "page" : undefined}
        >
          {tab.icon({ className: "h-4 w-4 shrink-0 opacity-90", "aria-hidden": true })}
          {tab.label}
        </button>
      ))}
    </nav>
  );
}

/** `TeamPageCard` from the old roster folder, unchanged in appearance. */
export function PanelCard({
  title,
  subtitle,
  children,
  variant = "default",
  headerRight,
  icon,
  bodyClassName,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  variant?: "default" | "emphasis" | "muted";
  headerRight?: ReactNode;
  icon?: ReactNode;
  bodyClassName?: string;
}) {
  const shellClass =
    variant === "muted"
      ? "border-b2b-border bg-b2b-cream/40"
      : variant === "emphasis"
        ? "border-b2b-accent/30"
        : "border-b2b-border bg-b2b-surface";

  return (
    <div className={`overflow-hidden rounded-lg border ${shellClass}`}>
      <div className="flex items-start gap-3 px-4 py-3 sm:px-5">
        {icon ? (
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-b2b-cream text-b2b-accent">
            {icon}
          </span>
        ) : null}
        <div className="min-w-0 flex-1">
          <h3 className="text-osce-body font-semibold tracking-tight text-b2b-headline">{title}</h3>
          {subtitle ? (
            <p className="mt-1 text-osce-caption leading-relaxed text-b2b-mid">{subtitle}</p>
          ) : null}
        </div>
        {headerRight ? <div className="shrink-0">{headerRight}</div> : null}
      </div>
      <div className={bodyClassName ?? "border-t border-b2b-border p-4 sm:p-5"}>{children}</div>
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
