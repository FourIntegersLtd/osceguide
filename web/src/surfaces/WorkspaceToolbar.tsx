"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { LuChevronRight, LuSearch } from "react-icons/lu";
import { isNavActive } from "@/foundation/navigation/isNavActive";
import type { NavItem } from "@/surfaces/contract";
import { WorkspaceJumpTo } from "@/surfaces/WorkspaceJumpTo";

/** Pages reached from inside a section rather than from the nav. */
const DEEP_PAGES: Record<string, string> = {
  debriefs: "Debriefs",
  transcripts: "Transcripts",
  library: "Library",
  stations: "Station",
  attempts: "Attempt",
  sessions: "Sessions",
  sittings: "Sittings",
  circuits: "Circuit",
  slots: "Review",
  trainee: "My training",
  mocks: "Practice sessions",
};

export interface WorkspaceToolbarProps {
  items: NavItem[];
  /** The crumb before the page when its nav item has no section. */
  rootLabel: string;
  sectionLabels: Record<string, string>;
  basePath: string;
}

/**
 * The 52px bar over every workspace page (canvas `train-dashboard`): where you
 * are, a ⌘K jump-to, and the assistant.
 */
export function WorkspaceToolbar({
  items,
  rootLabel,
  sectionLabels,
  basePath,
}: WorkspaceToolbarProps) {
  const pathname = usePathname() ?? "";
  const [jumpOpen, setJumpOpen] = useState(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setJumpOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const crumb = useMemo(() => {
    const match = items
      .filter((item) => isNavActive(pathname, item.href, { shellBase: basePath }))
      .sort((a, b) => b.href.length - a.href.length)[0];
    if (match) {
      return { section: match.section ? sectionLabels[match.section] : rootLabel, page: match.label };
    }
    const segment = pathname.slice(basePath.length).split("/").filter(Boolean)[0] ?? "";
    return { section: rootLabel, page: DEEP_PAGES[segment] ?? "Dashboard" };
  }, [items, pathname, basePath, sectionLabels, rootLabel]);

  return (
    <div className="sticky top-0 z-10 hidden h-[52px] shrink-0 items-center gap-3 border-b border-osce-border-light bg-osce-surface px-6 md:flex lg:px-10">
      <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1.5 text-[13px]">
        <span className="text-b2c-text-muted">{crumb.section}</span>
        <LuChevronRight className="h-3.5 w-3.5 shrink-0 text-osce-ink-400" aria-hidden />
        <span className="truncate font-medium text-osce-ink-900" aria-current="page">
          {crumb.page}
        </span>
      </nav>
      <div className="flex-1" />
      <button
        type="button"
        onClick={() => setJumpOpen(true)}
        className="hidden h-[30px] w-[220px] items-center gap-2 rounded-osce-md bg-b2c-surface-muted px-2.5 text-[13px] text-b2c-text-muted hover:bg-b2c-secondary-hover lg:flex"
      >
        <LuSearch className="h-3.5 w-3.5 shrink-0" aria-hidden />
        <span className="flex-1 text-left">Search</span>
        <kbd className="font-sans text-[11.5px] text-osce-ink-400">⌘K</kbd>
      </button>
      <button
        type="button"
        onClick={() => setJumpOpen(true)}
        aria-label="Search"
        className="inline-flex h-[30px] w-[30px] items-center justify-center rounded-osce-md text-b2c-text-secondary hover:bg-b2c-secondary lg:hidden"
      >
        <LuSearch className="h-4 w-4" aria-hidden />
      </button>
      {jumpOpen ? <WorkspaceJumpTo items={items} onClose={() => setJumpOpen(false)} /> : null}
    </div>
  );
}
