"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createElement, useCallback, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { LuLogOut, LuMenu, LuX } from "react-icons/lu";
import { Button, cn } from "@/foundation/ui";
import { useSession, can as hasPermission, type Permission } from "@/foundation/session";
import {
  SurfaceProvider,
  capabilitiesFor,
  NAV_SECTIONS,
  NAV_SECTION_LABELS,
} from "@/capabilities";
import { HelpPanel, type HelpNavItem } from "@/capabilities/help";
import type { NavItem, SurfaceManifest } from "@/surfaces/contract";
import { navFooterFor } from "@/surfaces/screens";
import { WorkspaceSwitcher } from "@/surfaces/WorkspaceSwitcher";
import type { Workspace } from "@/foundation/routing";

export interface SurfaceShellProps {
  manifest: SurfaceManifest;
  /** The workspace this shell is showing, or null for the staff console. */
  workspace: Workspace | null;
  /** Everything below this shell hangs off here, e.g. `/app/kings`. */
  basePath: string;
  children: ReactNode;
}

/**
 * The frame every arm shares.
 *
 * There used to be five of these, one per arm, each re-deciding the same
 * things. Now there is one, and an arm is a manifest: its label, its
 * navigation and which workspaces reach it. `data-surface` is the whole of the
 * visual difference between them — the primitives read their colours from the
 * custom properties that attribute selects, so nothing below here branches on
 * which arm it is in.
 *
 * Navigation is decided once, from the arm's own items plus whatever
 * `capabilitiesFor` says this surface mounts, and that list is handed to the
 * help panel. That is how the assistant can say "open Study material" on an
 * institution screen without anybody scripting it.
 */
export function SurfaceShell({ manifest, workspace, basePath, children }: SurfaceShellProps) {
  const { session, signOut } = useSession();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const href = useCallback((path: string) => `${basePath}${path}`, [basePath]);

  const items = useMemo<NavItem[]>(() => {
    const own = manifest.nav({
      // The staff console has no workspace; its nav does not read one.
      workspace: workspace ?? ({ kind: "personal" } as Workspace),
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
  }, [manifest, workspace, session, href, basePath]);

  /**
   * The sidebar, grouped.
   *
   * An arm whose items name no section gets one flat list, which is what this
   * used to be for everybody and what the institution arms still want. The
   * consumer arm names them, and then this draws the retiring client's three
   * headed groups — Practice, Connect, General — in its order.
   */
  const groups = useMemo(() => {
    const ungrouped = items.filter((item) => !item.section);
    const sections = NAV_SECTIONS.map((section) => ({
      section,
      label: NAV_SECTION_LABELS[section],
      items: items.filter((item) => item.section === section),
    })).filter((group) => group.items.length > 0);
    return { ungrouped, sections };
  }, [items]);

  const renderItem = useCallback(
    (item: NavItem) => {
      const active =
        pathname === item.href ||
        (item.href !== basePath && pathname?.startsWith(`${item.href}/`));
      const Icon = item.icon;
      return (
        <Link
          key={item.key}
          href={item.href}
          onClick={() => setMenuOpen(false)}
          aria-current={active ? "page" : undefined}
          className={cn(
            "flex items-center gap-2.5 rounded-control px-3 py-2 text-sm transition-colors",
            active
              ? "bg-accent-subtle font-medium text-accent"
              : "text-ink-muted hover:bg-surface-raised hover:text-ink",
          )}
        >
          {Icon && <Icon className="h-4 w-4 shrink-0" />}
          {item.label}
        </Link>
      );
    },
    [pathname, basePath],
  );

  const navFooter = navFooterFor(manifest);

  const helpNav = useMemo<HelpNavItem[]>(
    () => items.map((item) => ({ key: item.key, label: item.label, path: item.href })),
    [items],
  );

  return (
    <SurfaceProvider
      surface={manifest.id}
      orgSlug={workspace?.orgSlug ?? null}
      basePath={basePath}
    >
      <div
        data-surface={manifest.id}
        /*
         * The product stylesheet's app-shell scope: Inter at 16px for body,
         * Archivo for headings, and the document scroll locked so the sidebar
         * and the content region scroll independently. Every signed-in screen
         * is inside this.
         */
        data-b2c-shell=""
        className="flex min-h-screen bg-canvas text-ink"
      >
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-control focus:bg-surface focus:px-3 focus:py-2"
        >
          Skip to content
        </a>

        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-40 w-64 shrink-0 border-r border-border bg-surface transition-transform md:static md:translate-x-0",
            menuOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <div className="flex h-14 items-center gap-2 border-b border-border px-3">
            <div className="min-w-0 flex-1">
              {workspace ? (
                <WorkspaceSwitcher current={workspace} />
              ) : (
                <span className="truncate text-sm font-semibold text-ink">{manifest.label}</span>
              )}
            </div>
            <button
              type="button"
              className="md:hidden"
              onClick={() => setMenuOpen(false)}
              aria-label="Close menu"
            >
              <LuX className="h-5 w-5 text-ink-muted" aria-hidden />
            </button>
          </div>

          <nav
            className="flex h-[calc(100%-3.5rem)] flex-col overflow-y-auto p-3"
            aria-label={`${manifest.label} sections`}
          >
            <div className="flex flex-col gap-0.5">{groups.ungrouped.map(renderItem)}</div>

            {groups.sections.map((group) => (
              <div key={group.section} className="mt-4 first:mt-0">
                <p className="px-3 pb-1.5 font-mono text-[0.6875rem] uppercase tracking-wider text-ink-muted">
                  {group.label}
                </p>
                <div className="flex flex-col gap-0.5">{group.items.map(renderItem)}</div>
              </div>
            ))}

            {/*
              * `createElement` rather than a capitalised local rendered as
              * JSX, for the reason `app/[workspace]/screen.tsx` gives: the
              * React Compiler reads that as defining a component during
              * render. This is a lookup in a table fixed at module scope.
              */}
            {navFooter && createElement(navFooter)}
          </nav>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex h-14 items-center justify-between gap-3 border-b border-border bg-surface px-4">
            <button
              type="button"
              className="md:hidden"
              onClick={() => setMenuOpen(true)}
              aria-label="Open menu"
            >
              <LuMenu className="h-5 w-5 text-ink-muted" aria-hidden />
            </button>
            <div className="min-w-0 flex-1" />
            <div className="flex items-center gap-3">
              <span className="hidden truncate text-sm text-ink-muted sm:block">
                {session?.user.email}
              </span>
              <Button variant="ghost" size="sm" onClick={() => void signOut()}>
                <LuLogOut className="h-4 w-4" aria-hidden />
                <span className="sr-only sm:not-sr-only">Sign out</span>
              </Button>
            </div>
          </header>

          <main id="main" className="min-w-0 flex-1 px-4 py-6 md:px-8">
            <div className="mx-auto w-full max-w-6xl">{children}</div>
          </main>
        </div>

        <HelpPanel navItems={helpNav} />
      </div>
    </SurfaceProvider>
  );
}
