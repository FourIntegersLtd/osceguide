"use client";

import { useCallback } from "react";
import { GoSidebarCollapse } from "react-icons/go";
import { MdClose, MdMenu } from "react-icons/md";
import Logo from "@/foundation/ui/Logo";
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
  basePath: string;
  groups: NavRailGroups;
  navCollapsed: boolean;
  onNavCollapsedChange: (collapsed: boolean) => void;
  menuOpen: boolean;
  onMenuOpenChange: (open: boolean) => void;
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
  basePath,
  groups,
  navCollapsed,
  onNavCollapsedChange,
  menuOpen,
  onMenuOpenChange,
}: WorkspaceSidebarProps) {
  const ariaLabel = `${label} sections`;
  const closeMenu = useCallback(() => onMenuOpenChange(false), [onMenuOpenChange]);

  return (
    <>
      <header
        className={`fixed top-0 left-0 z-20 flex h-14 w-full items-center justify-between px-4 md:hidden ${b2cNavMobileBar}`}
      >
        <button
          type="button"
          onClick={() => onMenuOpenChange(!menuOpen)}
          aria-expanded={menuOpen}
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          className={b2cIconButton}
        >
          {menuOpen ? <MdClose className="h-5 w-5" /> : <MdMenu className="h-5 w-5" />}
        </button>
        <Logo variant="light" interactive={false} />
        <div className="h-11 w-11 shrink-0" aria-hidden />
      </header>

      <div
        className={cn(
          "fixed top-0 left-0 z-50 flex h-[100dvh] flex-col overflow-hidden border-r md:border-r-0",
          b2cNavShell,
          "w-[240px] md:w-20",
          navCollapsed ? "lg:w-20" : "lg:w-[240px]",
          "md:transition-all md:duration-300 md:ease-in-out",
          menuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        <div className={cn("px-3 pt-4 md:px-2", navCollapsed ? "lg:px-2" : "lg:px-3")}>
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
                <GoSidebarCollapse className="h-4 w-4 rotate-180" />
              </button>
            </div>
          ) : (
            <div className="group hidden items-center justify-between px-2.5 pb-4 pt-1 lg:flex">
              <Logo variant="light" />
              <button
                type="button"
                onClick={() => onNavCollapsedChange(true)}
                aria-label="Collapse sidebar"
                className={cn(b2cIconButton, "opacity-0 focus:opacity-100 group-hover:opacity-100 sm:h-7 sm:w-7")}
              >
                <GoSidebarCollapse className="h-4 w-4" />
              </button>
            </div>
          )}
          <div className="px-2.5 pb-4 pt-1 md:hidden">
            <Logo variant="light" />
          </div>
          <div className={cn("mb-1.5 md:hidden", navCollapsed ? "lg:hidden" : "lg:block")}>
            <WorkspaceSwitcher current={workspace} detail={detail} />
          </div>
        </div>

        <NavRailList
          className="hidden md:flex lg:hidden"
          groups={groups}
          basePath={basePath}
          collapsed
          onNavigate={closeMenu}
          ariaLabel={ariaLabel}
          footer={<WorkspaceNavFooter consumer={consumer} collapsed />}
        />
        <NavRailList
          className="hidden lg:flex"
          groups={groups}
          basePath={basePath}
          collapsed={navCollapsed}
          onNavigate={closeMenu}
          ariaLabel={ariaLabel}
          footer={<WorkspaceNavFooter consumer={consumer} collapsed={navCollapsed} />}
        />
        <NavRailList
          className="flex md:hidden"
          groups={groups}
          basePath={basePath}
          collapsed={false}
          onNavigate={closeMenu}
          ariaLabel={ariaLabel}
          footer={<WorkspaceNavFooter consumer={consumer} />}
        />
      </div>
      {menuOpen ? (
        <button
          type="button"
          aria-label="Close menu"
          tabIndex={-1}
          onClick={closeMenu}
          className="fixed inset-0 z-40 bg-osce-ink-900/20 md:hidden"
        />
      ) : null}
    </>
  );
}
