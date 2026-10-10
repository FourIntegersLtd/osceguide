"use client";

import { useCallback } from "react";
import { LuPanelLeftClose, LuPanelLeftOpen } from "react-icons/lu";
import { MdClose, MdMenu, MdRefresh } from "react-icons/md";
import Logo from "@/foundation/ui/Logo";
import { useStandaloneDisplay } from "@/foundation/pwa/standalone";
import { cn } from "@/foundation/ui";
import { b2cIconButton, b2cNavMobileBar, b2cNavShell } from "@/foundation/ui/productTokens";
import { NavRailList, type NavRailGroups } from "@/surfaces/NavRailList";
import { WorkspaceNavFooter } from "@/surfaces/WorkspaceNavFooter";
import { WorkspaceSwitcher } from "@/surfaces/WorkspaceSwitcher";
import type { Workspace } from "@/foundation/routing";

export interface WorkspaceSidebarProps {
  workspace: Workspace;
  /** The arm, for the nav landmark: "Institution sections". */
  label: string;
  /** The line under the workspace name: the exam on Train, the arm elsewhere. */
  detail: string | null;
  /** Train only: the upgrade button and exam countdown at the foot. */
  consumer: boolean;
  /** The staff console: a fixed name instead of the workspace switcher. */
  staff?: boolean;
  basePath: string;
  groups: NavRailGroups;
  navCollapsed: boolean;
  onNavCollapsedChange: (collapsed: boolean) => void;
  menuOpen: boolean;
  onMenuOpenChange: (open: boolean) => void;
  /** Unread inbox messages: a dot on the phone menu button. */
  unread?: number;
}

/**
 * The workspace sidebar from the canvas: 240px on the grey canvas, the logo,
 * which workspace you are in, the nav sections, and you at the foot. A drawer on phones, an icon rail on tablets, collapsible on lg.
 */
export function WorkspaceSidebar({
  workspace,
  label,
  detail,
  consumer,
  staff = false,
  basePath,
  groups,
  navCollapsed,
  onNavCollapsedChange,
  menuOpen,
  onMenuOpenChange,
  unread = 0,
}: WorkspaceSidebarProps) {
  const ariaLabel = `${label} sections`;
  const standalone = useStandaloneDisplay();
  const closeMenu = useCallback(() => onMenuOpenChange(false), [onMenuOpenChange]);

  return (
    <>
      <header
        className={`fixed top-0 left-0 z-20 flex h-14 w-full items-center gap-2 px-4 md:hidden ${b2cNavMobileBar}`}
      >
        <button
          type="button"
          onClick={() => onMenuOpenChange(!menuOpen)}
          aria-expanded={menuOpen}
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          className={`${b2cIconButton} relative`}
        >
          {menuOpen ? <MdClose className="h-5 w-5" /> : <MdMenu className="h-5 w-5" />}
          {unread > 0 && !menuOpen ? (
            <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-osce-accent" aria-hidden />
          ) : null}
        </button>
        <Logo variant="light" interactive={false} />
        {/* The installed app has no browser toolbar, so no way to reload a
            screen that has stuck. In a browser tab the browser's own is enough. */}
        {standalone ? (
          <button
            type="button"
            onClick={() => window.location.reload()}
            aria-label="Reload"
            className={cn(b2cIconButton, "ml-auto")}
          >
            <MdRefresh className="h-5 w-5" />
          </button>
        ) : null}
      </header>

      <div
        className={cn(
          // On phones the drawer opens under the top bar, so its logo and
          // close button stay the only ones on screen.
          "fixed top-14 left-0 z-50 flex h-[calc(100dvh-3.5rem)] flex-col overflow-hidden border-r md:top-0 md:h-[100dvh] md:border-r-0",
          b2cNavShell,
          "w-72 max-w-[85vw] md:w-20 md:max-w-none",
          navCollapsed ? "lg:w-20" : "lg:w-[240px]",
          "md:transition-all md:duration-300 md:ease-in-out",
          menuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        <div className={cn("px-3 pt-3 md:px-2 md:pt-4", navCollapsed ? "lg:px-2" : "lg:px-3")}>
          <div className="hidden flex-col items-center gap-2 pb-3 md:flex lg:hidden">
            <Logo variant="light" compact />
          </div>
          {navCollapsed ? (
            <div className="hidden flex-col items-center gap-2 pb-3 lg:flex">
              <Logo variant="light" compact />
              <button
                type="button"
                onClick={() => onNavCollapsedChange(false)}
                aria-label="Expand sidebar"
                className={b2cIconButton}
              >
                <LuPanelLeftOpen className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div className="group hidden items-center justify-between px-2.5 pb-4 pt-1 lg:flex">
              <Logo variant="light" />
              <button
                type="button"
                onClick={() => onNavCollapsedChange(true)}
                aria-label="Collapse sidebar"
                className={cn(b2cIconButton, "sm:h-7 sm:w-7")}
              >
                <LuPanelLeftClose className="h-4 w-4" />
              </button>
            </div>
          )}
          <div className={cn("mb-1.5 md:hidden", navCollapsed ? "lg:hidden" : "lg:block")}>
            {staff ? (
              <div className="hidden min-h-11 items-center px-2.5 lg:flex">
                <span className="min-w-0 flex-1 text-left">
                  <span className="block truncate text-[13.5px] font-semibold leading-[18px] text-osce-ink-900">
                    Platform console
                  </span>
                  <span className="block truncate text-osce-caption font-normal text-b2c-text-muted">
                    OSCE Guide staff
                  </span>
                </span>
              </div>
            ) : (
              <WorkspaceSwitcher current={workspace} detail={detail} />
            )}
          </div>
        </div>

        <NavRailList
          className="hidden md:flex lg:hidden"
          groups={groups}
          basePath={basePath}
          collapsed
          onNavigate={closeMenu}
          ariaLabel={ariaLabel}
          footer={<WorkspaceNavFooter consumer={consumer} staff={staff} collapsed />}
        />
        <NavRailList
          className="hidden lg:flex"
          groups={groups}
          basePath={basePath}
          collapsed={navCollapsed}
          onNavigate={closeMenu}
          ariaLabel={ariaLabel}
          footer={<WorkspaceNavFooter consumer={consumer} staff={staff} collapsed={navCollapsed} />}
        />
        <NavRailList
          className="flex md:hidden"
          groups={groups}
          basePath={basePath}
          collapsed={false}
          onNavigate={closeMenu}
          ariaLabel={ariaLabel}
          footer={<WorkspaceNavFooter consumer={consumer} staff={staff} />}
        />
      </div>
      {menuOpen ? (
        <button
          type="button"
          aria-label="Close menu"
          tabIndex={-1}
          onClick={closeMenu}
          className="fixed inset-x-0 top-14 bottom-0 z-40 bg-osce-ink-900/20 md:hidden"
        />
      ) : null}
    </>
  );
}
