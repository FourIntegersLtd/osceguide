"use client";

import { useCallback, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { b2cPageColumn, b2cShellMain } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui";
import { useSession, can as hasPermission, type Permission } from "@/foundation/session";
import {
  SurfaceProvider,
  capabilitiesFor,
  NAV_SECTIONS,
  NAV_SECTION_LABELS,
} from "@/capabilities";
import { LazyB2CHelpDock } from "@/capabilities/help/LazyB2CHelpDock";
import type { HelpNavItem } from "@/capabilities/help/B2CHelpDock";
import type { NavItem, SurfaceManifest } from "@/surfaces/contract";
import { PlatformSidebar } from "@/surfaces/platform/PlatformSidebar";
import type { Workspace } from "@/foundation/routing";

export interface PlatformStaffShellProps {
  manifest: SurfaceManifest;
  basePath: string;
  children: ReactNode;
}

/** OSCE Guide staff console — same B2C rail, help dock and typography as `/app/me`. */
export function PlatformStaffShell({ manifest, basePath, children }: PlatformStaffShellProps) {
  const { session } = useSession();
  const [menuOpen, setMenuOpen] = useState(false);
  const [navCollapsed, setNavCollapsed] = useState(false);
  const [helpExpanded, setHelpExpanded] = useState(false);
  const [helpWide, setHelpWide] = useState(false);

  const href = useCallback((path: string) => `${basePath}${path}`, [basePath]);

  const items = useMemo<NavItem[]>(() => {
    const own = manifest.nav({
      workspace: { kind: "personal" } as Workspace,
      can: (permission: Permission) => hasPermission(session, permission),
      href,
    });
    const mounted = capabilitiesFor(manifest.id, {
      can: session?.capabilities.can ?? {},
      basePath,
    }).map((capability) => ({
      key: capability.id,
      label: capability.title,
      href: capability.href,
      icon: capability.icon,
      section: capability.section,
    }));
    return [...own, ...mounted];
  }, [manifest, session, href, basePath]);

  const groups = useMemo(() => {
    const ungrouped = items.filter((item) => !item.section);
    const sections = NAV_SECTIONS.map((section) => ({
      section,
      label: NAV_SECTION_LABELS[section],
      items: items.filter((item) => item.section === section),
    })).filter((group) => group.items.length > 0);
    return { ungrouped, sections };
  }, [items]);

  const helpNav = useMemo<HelpNavItem[]>(
    () => items.map((item) => ({ key: item.key, label: item.label, path: item.href })),
    [items],
  );

  return (
    <SurfaceProvider surface={manifest.id} orgSlug={null} basePath={basePath}>
      <div
        data-surface={manifest.id}
        data-b2c-shell=""
        className={cn(
          "flex h-dvh max-h-dvh flex-col overflow-hidden bg-b2c-surface-muted font-sans text-osce-body text-osce-ink-900 antialiased",
          "md:grid md:grid-cols-[5rem_1fr_0fr] md:transition-[grid-template-columns] md:duration-300 md:ease-in-out",
          helpExpanded && !navCollapsed && (helpWide ? "lg:grid-cols-[14.5rem_1fr_36rem]" : "lg:grid-cols-[14.5rem_1fr_22rem]"),
          helpExpanded && navCollapsed && (helpWide ? "lg:grid-cols-[5rem_1fr_36rem]" : "lg:grid-cols-[5rem_1fr_22rem]"),
          !helpExpanded && !navCollapsed && "lg:grid-cols-[14.5rem_1fr_0fr]",
          !helpExpanded && navCollapsed && "lg:grid-cols-[5rem_1fr_0fr]",
        )}
      >
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-osce-surface focus:px-3 focus:py-2"
        >
          Skip to content
        </a>

        <div className="h-auto lg:h-full">
          <PlatformSidebar
            title={manifest.label}
            basePath={basePath}
            groups={groups}
            navCollapsed={navCollapsed}
            onNavCollapsedChange={setNavCollapsed}
            menuOpen={menuOpen}
            onMenuOpenChange={setMenuOpen}
          />
        </div>

        <main
          id="main"
          data-b2c-scroll=""
          className={cn(b2cShellMain, "flex min-h-0 min-w-0 flex-1 flex-col md:col-span-1")}
        >
          <div className={b2cPageColumn}>{children}</div>
        </main>

        <LazyB2CHelpDock
          navItems={helpNav}
          isExpanded={helpExpanded}
          setIsExpanded={setHelpExpanded}
          isWide={helpWide}
          setIsWide={setHelpWide}
          appType="platform"
        />
      </div>
    </SurfaceProvider>
  );
}
