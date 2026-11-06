"use client";

import type { KeyboardEvent } from "react";
import { Badge, cn } from "@/foundation/ui";
import { boardTab, boardTabs } from "@/foundation/ui/boardKit";
import { SCHEME_TABS } from "@/capabilities/authoring/rubrics/schemeTabs";
import type { SchemeTabId } from "@/capabilities/authoring/rubrics/schemeModel";

/** The scheme's tabs with a red count on those that hold problems; arrow keys, Home and End move between them. */
export function SchemeTabBar({ tab, redCount, onGo }: { tab: SchemeTabId; redCount: (id: SchemeTabId) => number; onGo: (id: SchemeTabId) => void }) {
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const at = SCHEME_TABS.findIndex((t) => t.id === tab);
    const to = event.key === "ArrowRight" ? (at + 1) % SCHEME_TABS.length : event.key === "ArrowLeft" ? (at + SCHEME_TABS.length - 1) % SCHEME_TABS.length : event.key === "Home" ? 0 : event.key === "End" ? SCHEME_TABS.length - 1 : null;
    const target = to === null ? undefined : SCHEME_TABS[to];
    if (!target) return;
    event.preventDefault();
    onGo(target.id);
    event.currentTarget.parentElement?.querySelector<HTMLElement>(`#scheme-tab-${target.id}`)?.focus();
  };
  return (
    <div role="tablist" aria-label="Marking scheme" className={boardTabs}>
      {SCHEME_TABS.map((t, n) => {
        const red = redCount(t.id);
        const on = tab === t.id;
        return (
          <button
            key={t.id}
            id={`scheme-tab-${t.id}`}
            type="button"
            role="tab"
            aria-selected={on}
            aria-controls="scheme-panel"
            tabIndex={on ? 0 : -1}
            onClick={() => onGo(t.id)}
            onKeyDown={onKeyDown}
            className={cn(boardTab(on), "flex items-center gap-1.5")}
          >
            <span className="text-osce-caption text-ink-subtle">{n + 1}</span>
            {t.label}
            {red > 0 ? <Badge variant="danger" size="sm">{red}</Badge> : null}
          </button>
        );
      })}
    </div>
  );
}
