"use client";

import { useCallback, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { b2cPageColumn, b2cShellMain } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui";
import { useCurrentExam, useSession, can as hasPermission, type Permission } from "@/foundation/session";
import {
  SurfaceProvider,
  capabilitiesFor,
  NAV_SECTIONS,
  NAV_SECTION_LABELS,
  NAV_DEEP_PAGES,
} from "@/capabilities";
import { InboxUnreadProvider, useInboxUnread } from "@/capabilities/inbox";
import ChooseExam from "@/capabilities/account/ChooseExam";
import { LazyB2CHelpDock } from "@/capabilities/help/LazyB2CHelpDock";
import { PeerPracticeProvider } from "@/capabilities/peer-practice/PeerPracticeProvider";
import { PendingFeedbackProvider } from "@/capabilities/pending-feedback";
import type { HelpNavItem } from "@/capabilities/help/api";
import type { NavItem, SurfaceManifest } from "@/surfaces/contract";
import { examDetail } from "@/surfaces/examSwitcher";
import { WorkspaceSidebar } from "@/surfaces/WorkspaceSidebar";
import { WorkspaceToolbar } from "@/surfaces/WorkspaceToolbar";
import { PERSONAL_WORKSPACE, type Workspace } from "@/foundation/routing";

export interface WorkspaceShellProps {
  manifest: SurfaceManifest;
  /** Absent on the staff console, which belongs to no workspace. */
  workspace?: Workspace;
  basePath: string;
  children: ReactNode;
}

/**
 * The shell of every workspace (canvas `train-dashboard`, `assess-overview`):
 * the sidebar on the grey canvas, a white main panel with the toolbar over
 * it, and the help dock. Train adds what only a consumer has: the exam gate,
 * the exam under the workspace name, and peer practice.
 */
export function WorkspaceShell({
  manifest,
  workspace = PERSONAL_WORKSPACE,
  basePath,
  children,
}: WorkspaceShellProps) {
  const { session } = useSession();
  const isTrain = manifest.id === "train";
  const staff = manifest.id === "platform";
  // The marketplace is SCA-only in navigation, like the retiring `scaOnly`.
  const { code: examCode } = useCurrentExam();
  const [menuOpen, setMenuOpen] = useState(false);
  const [navCollapsed, setNavCollapsed] = useState(false);
  const [helpExpanded, setHelpExpanded] = useState(false);
  const [helpWide, setHelpWide] = useState(false);

  const href = useCallback((path: string) => `${basePath}${path}`, [basePath]);

  const items = useMemo<NavItem[]>(() => {
    const own = manifest.nav({
      workspace,
      can: (permission: Permission) => hasPermission(session, permission),
      href,
    });
    const mounted = capabilitiesFor(manifest.id, {
      can: session?.capabilities.can ?? {},
      basePath,
      examCode,
    }).map((capability) => ({
      key: capability.id,
      label: capability.title,
      href: capability.href,
      icon: capability.icon,
      section: capability.section,
    }));
    return [...own, ...mounted];
  }, [manifest, workspace, session, href, basePath, examCode]);

  // Only an arm that mounts the inbox asks for the count; staff and
  // institution shells never make the request.
  const inboxItem = items.find((item) => item.key === "inbox");
  const unread = useInboxUnread(Boolean(inboxItem));

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

  // A consumer app with no exam shows every exam's plans and no exam's
  // library, so an account without one answers that first.
  if (isTrain && session && !session.user.exam_code) return <ChooseExam />;

  return (
    <SurfaceProvider surface={manifest.id} orgSlug={workspace.orgSlug ?? null} basePath={basePath}>
      <InboxUnreadProvider value={unread} enabled={Boolean(inboxItem)}>
      <div
        data-surface={manifest.id}
        data-b2c-shell=""
        className={cn(
          "flex h-dvh max-h-dvh flex-col overflow-hidden bg-osce-canvas font-sans text-osce-body text-osce-ink-900 antialiased",
          "md:grid md:grid-cols-[5rem_1fr_0fr] md:transition-[grid-template-columns] md:duration-300 md:ease-in-out",
          helpExpanded && !navCollapsed && (helpWide ? "lg:grid-cols-[15rem_1fr_36rem]" : "lg:grid-cols-[15rem_1fr_22rem]"),
          helpExpanded && navCollapsed && (helpWide ? "lg:grid-cols-[5rem_1fr_36rem]" : "lg:grid-cols-[5rem_1fr_22rem]"),
          !helpExpanded && !navCollapsed && "lg:grid-cols-[15rem_1fr_0fr]",
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
          <WorkspaceSidebar
            workspace={workspace}
            label={manifest.label}
            detail={isTrain ? examDetail(examCode ?? null, session?.user.exam_date ?? null) : manifest.label}
            consumer={isTrain}
            staff={staff}
            basePath={basePath}
            groups={groups}
            navCollapsed={navCollapsed}
            onNavCollapsedChange={setNavCollapsed}
            menuOpen={menuOpen}
            onMenuOpenChange={setMenuOpen}
            unread={unread.count}
          />
        </div>

        <div className="relative flex min-h-0 min-w-0 flex-1 flex-col bg-osce-surface md:border-l md:border-osce-border">
          <WorkspaceToolbar
            items={items}
            rootLabel={isTrain ? "Practice" : staff ? "Platform console" : workspace.name}
            sectionLabels={NAV_SECTION_LABELS}
            deepPages={NAV_DEEP_PAGES}
            basePath={basePath}
            examCode={examCode ?? null}
            consumer={isTrain}
          />
          <main
            id="main"
            data-b2c-scroll=""
            className={cn(b2cShellMain, "flex min-h-0 flex-1 flex-col")}
          >
            <div className={b2cPageColumn}>
              <div className="space-y-6 md:pt-7 lg:pt-9">
                <PendingFeedbackProvider>
                  {isTrain ? <PeerPracticeProvider>{children}</PeerPracticeProvider> : children}
                </PendingFeedbackProvider>
              </div>
            </div>
          </main>
        </div>

        <LazyB2CHelpDock
          navItems={helpNav}
          isExpanded={helpExpanded}
          setIsExpanded={setHelpExpanded}
          isWide={helpWide}
          setIsWide={setHelpWide}
        />
      </div>
      </InboxUnreadProvider>
    </SurfaceProvider>
  );
}
