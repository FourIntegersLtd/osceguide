"use client";

import { useId, type ReactNode } from "react";
import { AnchoredTooltip } from "@/foundation/ui/AnchoredTooltip";
import { boardIconBtn } from "@/foundation/ui/boardKit";
import { Spinner } from "@/foundation/ui/Spinner";

const TOOLTIP_CHIP =
  "pointer-events-none z-[200] w-max max-w-[240px] rounded-control bg-osce-ink-900 px-3 py-1.5 text-assess-meta text-white";

export type RowActionTone = "default" | "danger";

/**
 * The one way a board table row offers its actions: a single right-aligned line
 * of icon buttons, each named for assistive tech and explained by a tooltip.
 * Text buttons wrapped under a row were the clutter this replaces.
 * A row with more than one action does not line icons up here: it keeps at most one inline primary
 * and puts the rest in `ActionMenu` (the "⋯" menu).
 */
export function RowActions({ children }: { children: ReactNode }) {
  return <div className="ml-auto flex shrink-0 items-center justify-end gap-1.5">{children}</div>;
}

/**
 * `label` is the accessible name (and the word the confirm dialog uses);
 * `hint`, when given, is what the tooltip says instead, for the longer
 * "why" a bare label cannot carry. Pass the icon as the child.
 */
export function RowAction({
  label,
  hint,
  tone = "default",
  busy = false,
  disabled = false,
  onClick,
  children,
}: {
  label: string;
  hint?: string;
  tone?: RowActionTone;
  busy?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  children: ReactNode;
}) {
  const hintId = useId();
  const described = hint !== undefined && hint !== label;
  return (
    <AnchoredTooltip label={hint ?? label} placement="top" chipClassName={TOOLTIP_CHIP}>
      <button
        type="button"
        aria-label={label}
        aria-describedby={described ? hintId : undefined}
        aria-busy={busy || undefined}
        disabled={disabled || busy}
        onClick={onClick}
        className={boardIconBtn(tone)}
      >
        {busy ? <Spinner size="sm" className="text-current" label="Working" /> : children}
      </button>
      {described ? (
        <span id={hintId} className="sr-only">
          {hint}
        </span>
      ) : null}
    </AnchoredTooltip>
  );
}
