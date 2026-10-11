"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { LuBell, LuChevronRight, LuCircleHelp, LuSearch } from "react-icons/lu";
import { resolveCrumb } from "@/foundation/navigation/resolveCrumb";
import { getButtonClassName } from "@/foundation/ui";
import { openAthena } from "@/capabilities/help/api";
import { unreadLabel, useInboxUnreadContext } from "@/capabilities/inbox";
import type { NavItem } from "@/surfaces/contract";
import { WorkspaceJumpTo } from "@/surfaces/WorkspaceJumpTo";

export interface WorkspaceToolbarProps {
  items: NavItem[];
  /** The crumb before the page when its nav item has no section. */
  rootLabel: string;
  sectionLabels: Record<string, string>;
  deepPages: Record<string, string>;
  basePath: string;
  /** The learner's exam, for the library and Help searches. */
  examCode: string | null;
  /** Train only: the station library is searchable from here. */
  consumer: boolean;
}

/**
 * The 52px bar over every workspace page (canvas `train-dashboard`): where you
 * are, a ⌘K search over pages, stations and Help, and the Help button (outlined, so it does not read as part of the search field). Phones
 * have no toolbar; their Help button is the floating one (`AthenaFab`).
 */
export function WorkspaceToolbar({
  items,
  rootLabel,
  sectionLabels,
  deepPages,
  basePath,
  examCode,
  consumer,
}: WorkspaceToolbarProps) {
  const pathname = usePathname() ?? "";
  const [jumpOpen, setJumpOpen] = useState(false);
  const closeJump = useCallback(() => setJumpOpen(false), []);
  const unread = useInboxUnreadContext();
  const notificationsHref = items.find((item) => item.key === "inbox")?.href ?? null;
  const scope = useMemo(() => ({ examCode, stations: consumer }), [examCode, consumer]);

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

  const crumb = useMemo(
    () => resolveCrumb({ pathname, items, basePath, sectionLabels, rootLabel, deepPages }),
    [items, pathname, basePath, sectionLabels, rootLabel, deepPages],
  );

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
      {notificationsHref ? (
        <Link
          href={notificationsHref}
          aria-label={unread.count > 0 ? `Notifications, ${unread.count} unread` : "Notifications"}
          className="relative inline-flex h-[30px] w-[30px] items-center justify-center rounded-osce-md text-b2c-text-secondary hover:bg-b2c-secondary"
        >
          <LuBell className="h-4 w-4" aria-hidden />
          {unread.count > 0 ? (
            <span className="absolute -right-1 -top-1 min-w-[1.1rem] rounded-full bg-osce-accent px-1 text-center text-osce-caption font-semibold leading-[1.1rem] text-white">
              {unreadLabel(unread.count)}
            </span>
          ) : null}
        </Link>
      ) : null}
      <button
        type="button"
        onClick={() => openAthena()}
        className={getButtonClassName({ variant: "outline", size: "sm", className: "gap-2" })}
      >
        <LuCircleHelp className="h-4 w-4" aria-hidden />
        Help
      </button>
      {jumpOpen ? <WorkspaceJumpTo items={items} scope={scope} basePath={basePath} onClose={closeJump} /> : null}
    </div>
  );
}
