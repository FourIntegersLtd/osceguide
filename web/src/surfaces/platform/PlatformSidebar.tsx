"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback } from "react";
import { GoSidebarCollapse } from "react-icons/go";
import { MdClose, MdLogout, MdMenu } from "react-icons/md";
import Logo from "@/foundation/ui/Logo";
import { cn } from "@/foundation/ui";
import { isNavActive } from "@/foundation/navigation/isNavActive";
import {
  b2cNavLinkActive,
  b2cNavLinkInactive,
  b2cNavMobileBar,
  b2cNavSectionLabel,
  b2cNavShell,
  b2cScrollY,
} from "@/foundation/ui/productTokens";
import { useSession } from "@/foundation/session";
import type { NavItem } from "@/surfaces/contract";
import type { NavSection } from "@/capabilities";
import { StaffNavFooter } from "@/surfaces/platform/StaffNavFooter";

export interface PlatformSidebarProps {
  title: string;
  basePath: string;
  groups: {
    ungrouped: NavItem[];
    sections: { section: NavSection; label: string; items: NavItem[] }[];
  };
  navCollapsed: boolean;
  onNavCollapsedChange: (collapsed: boolean) => void;
  menuOpen: boolean;
  onMenuOpenChange: (open: boolean) => void;
}

export function PlatformSidebar({
  title,
  basePath,
  groups,
  navCollapsed,
  onNavCollapsedChange,
  menuOpen,
  onMenuOpenChange,
}: PlatformSidebarProps) {
  const pathname = usePathname();
  const { signOut } = useSession();

  const syncCollapsed = useCallback(
    (value: boolean) => {
      onNavCollapsedChange(value);
    },
    [onNavCollapsedChange],
  );

  const renderItem = useCallback(
    (item: NavItem) => {
      const active = isNavActive(pathname ?? "", item.href, { shellBase: basePath });
      const Icon = item.icon;
      return (
        <Link
          key={item.key}
          href={item.href}
          onClick={() => onMenuOpenChange(false)}
          aria-current={active ? "page" : undefined}
          className={active ? b2cNavLinkActive : b2cNavLinkInactive}
        >
          {Icon ? (
            <Icon
              className={cn(
                "h-5 w-5 shrink-0",
                active ? "text-osce-ink-900" : "text-b2c-text-muted",
              )}
              aria-hidden
            />
          ) : null}
          <span className="min-w-0 flex-1 truncate md:sr-only lg:not-sr-only">{item.label}</span>
        </Link>
      );
    },
    [pathname, basePath, onMenuOpenChange],
  );

  return (
    <>
      <header
        className={`fixed top-0 left-0 z-20 flex h-16 w-full items-center justify-between px-4 md:hidden ${b2cNavMobileBar}`}
      >
        <button
          type="button"
          onClick={() => onMenuOpenChange(!menuOpen)}
          aria-expanded={menuOpen}
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          className="flex h-10 w-10 items-center justify-center"
        >
          {menuOpen ? (
            <MdClose className="h-6 w-6 text-osce-ink-900" />
          ) : (
            <MdMenu className="h-6 w-6 text-osce-ink-900" />
          )}
        </button>
        <Logo variant="light" interactive={false} />
        <div className="h-10 w-10 shrink-0" aria-hidden />
      </header>

      <div
        className={cn(
          "fixed top-0 left-0 z-50 flex h-[100dvh] flex-col overflow-hidden border-r border-[#EDF1F5]",
          b2cNavShell,
          "w-[232px] md:w-20",
          navCollapsed ? "lg:w-20" : "lg:w-[232px]",
          "md:transition-all md:duration-300 md:ease-in-out",
          menuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        <div
          className={cn(
            "px-4 pt-5 md:px-2 md:pb-2 md:pt-5",
            navCollapsed ? "lg:px-2 lg:pb-2 lg:pt-5" : "lg:px-4 lg:pt-5",
          )}
        >
          <div className="hidden flex-col items-center gap-2 md:flex lg:hidden">
            <Logo variant="light" compact />
          </div>
          {navCollapsed ? (
            <div className="hidden flex-col items-center gap-2 lg:flex">
              <Logo variant="light" compact />
              <button
                type="button"
                onClick={() => syncCollapsed(false)}
                aria-label="Expand sidebar"
                className="flex h-9 w-9 items-center justify-center rounded-md text-osce-ink-600 hover:bg-osce-navActive"
              >
                <GoSidebarCollapse className="h-5 w-5 rotate-180" />
              </button>
            </div>
          ) : (
            <div className="hidden items-center justify-between lg:flex">
              <Logo variant="light" />
              <button
                type="button"
                onClick={() => syncCollapsed(true)}
                aria-label="Collapse sidebar"
                className="flex h-9 w-9 items-center justify-center rounded-md text-osce-ink-600 hover:bg-osce-navActive"
              >
                <GoSidebarCollapse className="h-5 w-5" />
              </button>
            </div>
          )}
          <div className="md:hidden">
            <Logo variant="light" />
          </div>
          <p
            className={cn(
              "mt-3 hidden truncate text-center font-sans text-osce-meta font-medium text-b2c-text-muted lg:block",
              navCollapsed && "lg:sr-only",
            )}
          >
            {title}
          </p>
        </div>

        <nav className="flex min-h-0 flex-1 flex-col" aria-label="Staff console">
          <div className={`${b2cScrollY} min-h-0 flex-1 py-4`}>
            <div className="flex flex-col px-2">
              {groups.ungrouped.length > 0 ? (
                <div className="mb-5 flex flex-col gap-0.5">{groups.ungrouped.map(renderItem)}</div>
              ) : null}
              {groups.sections.map((group) => (
                <div key={group.section} className="mb-5 last:mb-0">
                  <p className={`${b2cNavSectionLabel} md:sr-only lg:not-sr-only`}>{group.label}</p>
                  <div className="flex flex-col gap-0.5">
                    {group.items.map(renderItem)}
                    {group.section === "general" ? (
                      <button
                        type="button"
                        onClick={() => void signOut()}
                        className={`${b2cNavLinkInactive} w-full md:justify-center lg:justify-start`}
                      >
                        <MdLogout className="h-5 w-5 shrink-0 text-b2c-text-muted" aria-hidden />
                        <span className="md:sr-only lg:not-sr-only">Sign out</span>
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <StaffNavFooter collapsed={navCollapsed} />
        </nav>
      </div>
    </>
  );
}
