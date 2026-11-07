"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";
import { LuChevronDown, LuChevronLeft, LuChevronRight } from "react-icons/lu";
import { boardCard } from "@/foundation/ui/boardKit";
import { cn } from "@/foundation/ui/cn";
import { SPLIT, clampWidth, loadSplit, saveSplit, stepWidth } from "@/domains/assess/room/splitLayout";

/**
 * The room as one card: the tiles on the left, the side panel on the right, a single hairline between.
 * From the large breakpoint up the divider drags, folds and resets; below it the panel stacks under the
 * tiles as a folding section. The card is a fixed height, so each side scrolls inside it and the page does not.
 */
export function SplitCard({ main, side, sideTitle }: { main: ReactNode; side: ReactNode; sideTitle: string }) {
  const [width, setWidth] = useState<number>(SPLIT.initial);
  const [collapsed, setCollapsed] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(true);
  const card = useRef<HTMLDivElement>(null);
  const origin = useRef({ x: 0, width: 0 });
  const sheetId = useId();

  useEffect(() => {
    // Read after mount: the server render cannot know this browser's saved layout.
    const saved = loadSplit();
    /* eslint-disable react-hooks/set-state-in-effect */
    setWidth(saved.width);
    setCollapsed(saved.collapsed);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  const apply = (next: { width?: number; collapsed?: boolean }) => {
    const state = { width: next.width ?? width, collapsed: next.collapsed ?? collapsed };
    setWidth(state.width);
    setCollapsed(state.collapsed);
    saveSplit(state);
  };
  const container = () => card.current?.getBoundingClientRect().width;

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (collapsed) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    origin.current = { x: event.clientX, width };
    setDragging(true);
  }
  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!dragging) return;
    setWidth(clampWidth(origin.current.width + (origin.current.x - event.clientX), container()));
  }
  function onPointerUp() {
    if (!dragging) return;
    setDragging(false);
    saveSplit({ width, collapsed });
  }
  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      apply({ collapsed: !collapsed });
    } else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      apply({ width: stepWidth(width, event.key, event.shiftKey, container()), collapsed: false });
    }
  }

  return (
    <div
      ref={card}
      style={{ "--split-w": `${width}px` } as React.CSSProperties}
      className={cn(boardCard, "flex flex-col overflow-hidden lg:h-[max(520px,calc(100dvh-9rem))] lg:flex-row")}
    >
      <div className="min-w-0 flex-1 overflow-y-auto overscroll-contain p-4 [scrollbar-width:thin] sm:p-5">{main}</div>

      <div className="relative hidden w-px shrink-0 bg-osce-ink-100 lg:block">
        {/* A focusable separator is an interactive widget (WAI-ARIA window splitter). */}
        {/* eslint-disable jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex */}
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize the side panel"
          aria-valuenow={collapsed ? 0 : width}
          aria-valuemin={0}
          aria-valuemax={SPLIT.max}
          tabIndex={0}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onDoubleClick={() => apply({ width: SPLIT.initial, collapsed: false })}
          onKeyDown={onKeyDown}
          className={cn(
            "absolute inset-y-0 -left-1.5 w-3 touch-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent",
            collapsed ? "cursor-pointer" : "cursor-col-resize hover:bg-osce-accent/10",
            dragging && "bg-osce-accent/10",
          )}
        />
        {/* eslint-enable jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex */}
        <button
          type="button"
          aria-label={collapsed ? `Show ${sideTitle.toLowerCase()}` : `Hide ${sideTitle.toLowerCase()}`}
          onClick={() => apply({ collapsed: !collapsed })}
          className="absolute left-1/2 top-8 z-10 grid h-9 w-5 -translate-x-1/2 place-items-center rounded-full border border-osce-ink-200 bg-white text-osce-ink-500 shadow-sm hover:text-osce-ink-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent"
        >
          {collapsed ? <LuChevronLeft aria-hidden className="h-3.5 w-3.5" /> : <LuChevronRight aria-hidden className="h-3.5 w-3.5" />}
        </button>
      </div>

      <section
        aria-label={sideTitle}
        className={cn(
          "min-h-0 shrink-0 border-t border-osce-ink-100 lg:border-t-0 lg:w-[var(--split-w)]",
          !dragging && "lg:transition-[width] lg:duration-200 motion-reduce:lg:transition-none",
          collapsed && "lg:hidden",
        )}
      >
        <button
          type="button"
          aria-expanded={sheetOpen}
          aria-controls={sheetId}
          onClick={() => setSheetOpen(!sheetOpen)}
          className="flex h-11 w-full items-center justify-between px-4 text-assess-label font-medium text-osce-ink-900 lg:hidden"
        >
          {sideTitle}
          <LuChevronDown aria-hidden className={cn("h-4 w-4 text-osce-ink-500 transition-transform duration-150 motion-reduce:transition-none", sheetOpen && "rotate-180")} />
        </button>
        <div id={sheetId} className={cn("h-[60dvh] min-h-0 lg:h-full", !sheetOpen && "max-lg:hidden")}>
          {side}
        </div>
      </section>
    </div>
  );
}
