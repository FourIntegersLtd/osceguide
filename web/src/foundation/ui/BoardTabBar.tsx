"use client";

import type { KeyboardEvent, ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";
import { boardTab, boardTabs } from "@/foundation/ui/boardKit";

/** The DOM id of one tab, for a panel's `aria-labelledby`. */
export const boardTabId = (idPrefix: string, id: string) => `${idPrefix}-${id}`;

/** The tab `key` moves to from `at`: arrows wrap, Home and End jump; null for any other key. */
function nextIndex(key: string, at: number, count: number): number | null {
  if (key === "ArrowRight") return (at + 1) % count;
  if (key === "ArrowLeft") return (at + count - 1) % count;
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  return null;
}

export type BoardTabItem<Id extends string> = { id: Id; label: string; before?: ReactNode; after?: ReactNode };

/**
 * The board's tab track: one `role=tab` per item, ids `<idPrefix>-<id>`, controlling `panelId`.
 * Arrow keys, Home and End move between the tabs.
 */
export function BoardTabBar<Id extends string>({
  label,
  idPrefix,
  panelId,
  tabs,
  value,
  onChange,
  className,
}: {
  label: string;
  idPrefix: string;
  panelId: string;
  tabs: readonly BoardTabItem<Id>[];
  value: Id;
  onChange: (id: Id) => void;
  className?: string;
}) {
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const at = tabs.findIndex((t) => t.id === value);
    const to = nextIndex(event.key, at, tabs.length);
    const target = to === null ? undefined : tabs[to];
    if (!target) return;
    event.preventDefault();
    onChange(target.id);
    event.currentTarget.parentElement?.querySelector<HTMLElement>(`#${boardTabId(idPrefix, target.id)}`)?.focus();
  };
  return (
    <div role="tablist" aria-label={label} className={cn(boardTabs, className)}>
      {tabs.map((t) => {
        const on = value === t.id;
        return (
          <button
            key={t.id}
            id={boardTabId(idPrefix, t.id)}
            type="button"
            role="tab"
            aria-selected={on}
            aria-controls={panelId}
            tabIndex={on ? 0 : -1}
            onClick={() => onChange(t.id)}
            onKeyDown={onKeyDown}
            className={cn(boardTab(on), "flex items-center gap-1.5")}
          >
            {t.before}
            {t.label}
            {t.after}
          </button>
        );
      })}
    </div>
  );
}
