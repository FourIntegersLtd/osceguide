"use client";

import { Badge } from "@/foundation/ui";
import { BoardTabBar } from "@/foundation/ui/BoardTabBar";
import { SCHEME_TABS } from "@/capabilities/authoring/rubrics/schemeTabs";
import type { SchemeTabId } from "@/capabilities/authoring/rubrics/schemeModel";

/** The scheme's tabs with a red count on those that hold problems; arrow keys, Home and End move between them. */
export function SchemeTabBar({ tab, redCount, onGo }: { tab: SchemeTabId; redCount: (id: SchemeTabId) => number; onGo: (id: SchemeTabId) => void }) {
  const tabs = SCHEME_TABS.map((t, n) => {
    const red = redCount(t.id);
    return {
      id: t.id,
      label: t.label,
      before: <span className="text-osce-caption text-ink-subtle">{n + 1}</span>,
      after: red > 0 ? <Badge variant="danger" size="sm">{red}</Badge> : null,
    };
  });
  return <BoardTabBar label="Marking scheme" idPrefix="scheme-tab" panelId="scheme-panel" tabs={tabs} value={tab} onChange={onGo} />;
}
