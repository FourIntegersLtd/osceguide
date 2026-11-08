"use client";

import { useId, useState, useSyncExternalStore, type ReactNode } from "react";
import { LuChevronDown } from "react-icons/lu";
import { cn } from "@/foundation/ui/cn";
import { loadRail, saveRail, toggleRail, type RailOpen } from "@/domains/assess/sessions/railState";

const EMPTY: RailOpen = {};
let remembered: RailOpen | null = null;
const listeners = new Set<() => void>();
const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};
/** The same object until a section is toggled, as useSyncExternalStore requires. */
const snapshot = (): RailOpen => (remembered ??= loadRail());

/** Opens a section from elsewhere on the page (the ended hero's "Publish feedback") and brings it into view. */
export function openRailSection(id: string): void {
  remembered = { ...snapshot(), [id]: true };
  saveRail(remembered);
  listeners.forEach((listener) => listener());
  requestAnimationFrame(() => document.getElementById(`rail-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" }));
}

/**
 * One folding section of the console's right-hand rail.
 *
 * Closed unless `defaultOpen` or the person opened it before (remembered in this browser, never on the
 * server). Children stay mounted while folded so a live room or a half-written note is not lost by
 * closing it; `lazy` holds back a section whose content costs a request until it is first opened.
 */
export function RailSection({
  id,
  title,
  hint,
  defaultOpen = false,
  lazy = false,
  children,
  ...rest
}: {
  id: string;
  title: string;
  /** Quiet text beside the title: a count or a status. */
  hint?: ReactNode;
  defaultOpen?: boolean;
  lazy?: boolean;
  children: ReactNode;
} & { "data-board"?: string }) {
  const panelId = useId();
  const stored = useSyncExternalStore(subscribe, snapshot, () => EMPTY);
  const open = stored[id] ?? defaultOpen;
  // Once opened it stays mounted, so a lazy section loads once.
  const [opened, setOpened] = useState(open);
  if (open && !opened) setOpened(true);

  function toggle() {
    remembered = toggleRail({ ...stored, [id]: open }, id);
    saveRail(remembered);
    listeners.forEach((listener) => listener());
  }

  return (
    <section id={`rail-${id}`} className="border-t border-osce-border-light first:border-t-0" data-board={rest["data-board"]}>
      <h2 className="m-0">
        <button
          type="button"
          onClick={toggle}
          aria-expanded={open}
          aria-controls={panelId}
          className="flex min-h-12 w-full items-center gap-3 px-5 py-3.5 text-left text-assess-label font-medium text-osce-ink-900 hover:bg-osce-canvas focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent"
        >
          <span className="flex-1">{title}</span>
          {hint ? <span className="text-assess-meta font-normal text-osce-ink-500">{hint}</span> : null}
          <LuChevronDown aria-hidden className={cn("h-4 w-4 shrink-0 text-osce-ink-500 transition-transform", open && "rotate-180")} />
        </button>
      </h2>
      <div id={panelId} hidden={!open} className="flex flex-col gap-3.5 px-5 pb-5">
        {lazy && !opened ? null : children}
      </div>
    </section>
  );
}

/** The rail itself: one calm card holding its sections. */
export function Rail({ children }: { children: ReactNode }) {
  return <div className="overflow-hidden rounded-board bg-osce-surface shadow-sm ring-1 ring-osce-border-light">{children}</div>;
}
