"use client";

import { useCallback } from "react";
import { GoSidebarCollapse } from "react-icons/go";
import { MdClose, MdMenu } from "react-icons/md";
import Logo from "@/foundation/ui/Logo";
import { cn } from "@/foundation/ui";
import {
  b2cNavMobileBar,
  b2cNavShell,
} from "@/foundation/ui/productTokens";
import { useSession } from "@/foundation/session";
import { NavRailList, type NavRailGroups } from "@/surfaces/NavRailList";
import { StaffNavFooter } from "@/surfaces/platform/StaffNavFooter";

export interface PlatformSidebarProps {
  title: string;
  basePath: string;
  groups: NavRailGroups;
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
  const { signOut } = useSession();

  const closeMenu = useCallback(() => onMenuOpenChange(false), [onMenuOpenChange]);
  const handleSignOut = useCallback(() => {
    void signOut();
  }, [signOut]);

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
                onClick={() => onNavCollapsedChange(false)}
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
                onClick={() => onNavCollapsedChange(true)}
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
          {navCollapsed ? null : (
            <p className="mt-3 hidden truncate text-center font-sans text-osce-meta font-medium text-b2c-text-muted lg:block">
              {title}
            </p>
          )}
        </div>

        <NavRailList
          className="hidden md:flex lg:hidden"
          groups={groups}
          basePath={basePath}
          collapsed
          onNavigate={closeMenu}
          onSignOut={handleSignOut}
          ariaLabel="Staff console"
          footer={<StaffNavFooter collapsed />}
        />
        <NavRailList
          className="hidden lg:flex"
          groups={groups}
          basePath={basePath}
          collapsed={navCollapsed}
          onNavigate={closeMenu}
          onSignOut={handleSignOut}
          ariaLabel="Staff console"
          footer={<StaffNavFooter collapsed={navCollapsed} />}
        />
        <NavRailList
          className="flex md:hidden"
          groups={groups}
          basePath={basePath}
          collapsed={false}
          onNavigate={closeMenu}
          onSignOut={handleSignOut}
          ariaLabel="Staff console"
          footer={<StaffNavFooter />}
        />
      </div>
    </>
  );
}
