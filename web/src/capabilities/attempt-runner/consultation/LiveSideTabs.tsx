"use client";

import { useRef, type KeyboardEvent, type ReactNode } from "react";
import { useLocalPreference } from "@/foundation/hooks";
import { cn } from "@/foundation/ui";
import { AlertDot } from "./AlertDot";
import { sideTab, type SideTab } from "./sideTabPreference";

const TABS: ReadonlyArray<{ id: SideTab; label: string }> = [
  { id: "covered", label: "Covered" },
  { id: "cues", label: "Live cues" },
];

/**
 * The live column's two-way switch: what the candidate has covered, or their live non-verbal
 * cues. Both panels stay mounted and the inactive one is only `hidden`, so the coverage event
 * subscription and the cue display keep updating while the other tab is showing. When a warning
 * cue is active and "Covered" is showing, "Live cues" carries a small dot: no sound, no pop-up.
 */
export function LiveSideTabs({ coverage, cues, alert, defaultTab = "covered" }: {
  coverage: ReactNode;
  cues: ReactNode;
  alert: boolean;
  /** Used until the candidate chooses: cues once they have turned them on, otherwise covered. */
  defaultTab?: SideTab;
}) {
  const chosen = useLocalPreference(sideTab);
  const tab = chosen ?? defaultTab;
  const refs = useRef<Partial<Record<SideTab, HTMLButtonElement | null>>>({});

  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    const next: SideTab = tab === "covered" ? "cues" : "covered";
    sideTab.set(next);
    refs.current[next]?.focus();
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div role="tablist" aria-label="Live panel" className="flex gap-1 border-b border-osce-border px-4 pt-3">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            ref={(el) => {
              refs.current[id] = el;
            }}
            type="button"
            role="tab"
            id={`live-tab-${id}`}
            aria-selected={tab === id}
            aria-controls={`live-panel-${id}`}
            tabIndex={tab === id ? 0 : -1}
            onClick={() => sideTab.set(id)}
            onKeyDown={onKeyDown}
            className={cn(
              "relative -mb-px border-b-2 px-3 py-2 text-osce-meta font-medium focus:outline-none focus:ring-2 focus:ring-osce-accent",
              tab === id ? "border-osce-accent text-osce-ink-900" : "border-transparent text-b2c-text-muted hover:text-osce-ink-900",
            )}
          >
            {label}
            {id === "cues" && alert && tab !== "cues" && (
              <AlertDot className="ml-1.5 inline-block h-2 w-2 align-middle" />
            )}
          </button>
        ))}
      </div>
      <div id="live-panel-covered" role="tabpanel" aria-labelledby="live-tab-covered" hidden={tab !== "covered"} className="flex min-h-0 flex-1 flex-col [&[hidden]]:hidden">{coverage}</div>
      <div id="live-panel-cues" role="tabpanel" aria-labelledby="live-tab-cues" hidden={tab !== "cues"} className="flex min-h-0 flex-1 flex-col [&[hidden]]:hidden">{cues}</div>
    </div>
  );
}
