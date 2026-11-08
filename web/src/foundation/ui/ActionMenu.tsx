"use client";

import Link from "next/link";
import { useId, type ReactNode } from "react";
import { LuEllipsis } from "react-icons/lu";
import { boardIconBtn } from "@/foundation/ui/boardKit";
import { cn } from "@/foundation/ui/cn";
import { PopupMenu } from "@/foundation/ui/PopupMenu";

export type ActionMenuItem = {
  label: string;
  icon?: ReactNode;
  tone?: "default" | "danger";
  disabled?: boolean;
  /** Small muted text under the label; when the item is disabled it is also read out as the reason. */
  hint?: string;
  /** A heading shown above the first item of each run of items that share it (the employer's grouped menu). */
  group?: string;
  onSelect?: () => void;
  /** Renders the item as a link (next/link) instead of a button. */
  href?: string;
};

const ITEM =
  "flex min-h-11 w-full items-center gap-2.5 rounded-control px-3 py-2 text-left text-assess-label focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent md:min-h-9";
const TONES = {
  default: "text-osce-ink-900 hover:bg-osce-canvas focus-visible:bg-osce-canvas",
  danger: "text-osce-danger-text hover:bg-osce-canvas focus-visible:bg-osce-canvas",
} as const;

/**
 * The one way a row or header offers more than one action: a "⋯" button that opens a menu. A row or header
 * keeps at most one inline primary action; everything else goes here, with `tone: "danger"` items last
 * (they are separated by a divider whatever order they are passed in). The menu closes on select.
 * `label` names the trigger for assistive tech, e.g. "Actions for Amara Okafor".
 */
export function ActionMenu({ items, label = "More actions" }: { items: readonly ActionMenuItem[]; label?: string }) {
  const ordered = [...items.filter((i) => i.tone !== "danger"), ...items.filter((i) => i.tone === "danger")];
  const firstDanger = ordered.findIndex((i) => i.tone === "danger");
  const id = useId();
  return (
    <PopupMenu
      fixed
      className="min-w-48 border-osce-border bg-osce-surface shadow-lg"
      trigger={({ open, toggle }) => (
        <button type="button" aria-label={label} aria-haspopup="menu" aria-expanded={open} onClick={toggle} className={boardIconBtn()}>
          <LuEllipsis aria-hidden className="h-4 w-4" />
        </button>
      )}
    >
      {(close) =>
        ordered.map((item, n) => {
          const hintId = `${id}-${n}`;
          const body = (
            <>
              {item.icon ? <span aria-hidden className="shrink-0">{item.icon}</span> : null}
              <span className="min-w-0">
                <span className="block">{item.label}</span>
                {item.hint ? (
                  <span id={hintId} className="block text-assess-meta text-osce-ink-500">
                    {item.hint}
                  </span>
                ) : null}
              </span>
            </>
          );
          const describedBy = item.disabled && item.hint ? hintId : undefined;
          const className = cn(ITEM, TONES[item.tone ?? "default"]);
          return (
            <li key={item.label} role="none" className={n === firstDanger && n > 0 ? "mt-1 border-t border-osce-border-light pt-1" : undefined}>
              {item.group && item.group !== ordered[n - 1]?.group ? (
                <span className="block px-3 pb-0.5 pt-2 text-assess-meta font-medium text-osce-ink-500">{item.group}</span>
              ) : null}
              {item.href && !item.disabled ? (
                <Link role="menuitem" href={item.href} aria-describedby={describedBy} className={className} onClick={() => { close(); item.onSelect?.(); }}>
                  {body}
                </Link>
              ) : (
                <button
                  type="button"
                  role="menuitem"
                  disabled={item.disabled}
                  aria-describedby={describedBy}
                  className={cn(className, "disabled:cursor-not-allowed disabled:opacity-60")}
                  onClick={() => { close(); item.onSelect?.(); }}
                >
                  {body}
                </button>
              )}
            </li>
          );
        })
      }
    </PopupMenu>
  );
}
