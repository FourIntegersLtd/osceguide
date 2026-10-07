"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { AnchoredTooltip } from "@/foundation/ui";
import {
  b2bIconButtonGhost,
  b2bIconButtonPrimarySm,
  b2bIconButtonSm,
  b2bIconTooltipChipBase,
} from "@/foundation/ui/b2bTokens";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";
import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";

const iconFocus =
  "focus:outline-none focus:ring-2 focus:ring-osce-accent/20 focus:ring-offset-1";

const b2cIconSm = `inline-flex h-11 w-11 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-osce-md border border-border bg-osce-surface text-ink-muted hover:bg-surface-raised disabled:pointer-events-none disabled:opacity-50 ${iconFocus}`;
const b2cIconPrimary = `inline-flex h-11 w-11 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-osce-md border border-transparent bg-osce-accent text-white hover:bg-osce-accent-hover disabled:pointer-events-none disabled:opacity-50 ${iconFocus}`;
const b2cIconGhost = `inline-flex h-11 w-11 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-osce-md border-0 bg-transparent text-ink-subtle hover:bg-surface-raised hover:text-ink disabled:pointer-events-none disabled:opacity-50 ${iconFocus}`;
const b2cTooltipChip =
  "pointer-events-none z-[200] w-max max-w-[220px] rounded-osce-md bg-ink px-3 py-1.5 text-osce-caption text-white";

export type AuthoringIconActionVariant =
  | "default"
  | "primary"
  | "danger"
  | "warning"
  | "ghost";

type SharedProps = {
  label: string;
  busy?: boolean;
  busyLabel?: string;
  disabled?: boolean;
  variant?: AuthoringIconActionVariant;
  /** A write: hidden from anyone who cannot author. */
  write?: boolean;
  children: ReactNode;
};

type Props = SharedProps &
  (
    | { href: string; onClick?: never }
    | { href?: never; onClick: () => void }
  );

function variantClass(variant: AuthoringIconActionVariant, b2c: boolean): string {
  if (b2c) {
    switch (variant) {
      case "primary":
        return b2cIconPrimary;
      case "danger":
        return `${b2cIconSm} text-osce-danger-text hover:bg-osce-danger-bg`;
      case "warning":
        return `${b2cIconSm} text-osce-warning-text hover:bg-osce-warning-bg`;
      case "ghost":
        return b2cIconGhost;
      default:
        return b2cIconSm;
    }
  }
  switch (variant) {
    case "primary":
      return b2bIconButtonPrimarySm;
    case "danger":
      return `${b2bIconButtonSm} text-osce-danger-text hover:bg-osce-danger-bg`;
    case "warning":
      return `${b2bIconButtonSm} text-osce-warning-text hover:bg-osce-warning-bg`;
    case "ghost":
      return b2bIconButtonGhost;
    default:
      return b2bIconButtonSm;
  }
}

function ActionSpinner() {
  return (
    <span
      className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
      aria-hidden
    />
  );
}

/**
 * Icon-only row action with a hover/focus tooltip. Hide a control when it
 * cannot run — a disabled Publish next to a Published badge is the clutter
 * these rows used to be.
 */
export function AuthoringIconAction({
  label,
  busy = false,
  busyLabel,
  disabled,
  variant = "default",
  write = false,
  children,
  href,
  onClick,
}: Props) {
  const chrome = useAuthoringChrome();
  const canAuthor = useCanAuthor();
  if (write && !canAuthor) return null;
  const tooltip = busy ? (busyLabel ?? label) : label;
  const classes = variantClass(variant, chrome.b2c);
  const icon = busy ? <ActionSpinner /> : children;

  const control = href ? (
    <Link href={href} aria-label={tooltip} className={classes}>
      {icon}
    </Link>
  ) : (
    <button
      type="button"
      aria-label={tooltip}
      aria-busy={busy || undefined}
      disabled={disabled || busy}
      onClick={onClick}
      className={classes}
    >
      {icon}
    </button>
  );

  return (
    <AnchoredTooltip
      label={tooltip}
      placement="bottom"
      chipClassName={chrome.b2c ? b2cTooltipChip : b2bIconTooltipChipBase}
    >
      {control}
    </AnchoredTooltip>
  );
}

/** `write` marks a group made only of writes: it is hidden from anyone who cannot author. */
export function AuthoringRowActions({ children, write = false }: { children: ReactNode; write?: boolean }) {
  const canAuthor = useCanAuthor();
  if (write && !canAuthor) return null;
  return <div className="flex shrink-0 items-center gap-1">{children}</div>;
}
