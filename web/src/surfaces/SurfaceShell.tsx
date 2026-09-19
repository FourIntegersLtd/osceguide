"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState } from "react";
import type { ComponentType, ReactNode } from "react";
import { LuLogOut, LuMenu, LuX } from "react-icons/lu";
import { Button, cn } from "@/foundation/ui";
import { RequireSession, useSession } from "@/foundation/session";
import { SurfaceProvider, capabilitiesFor, type Surface } from "@/capabilities";
import { HelpPanel, type HelpNavItem } from "@/capabilities/help";

export interface NavItem {
  key: string;
  label: string;
  href: string;
  icon?: ComponentType<{ className?: string }>;
}

export interface SurfaceShellProps {
  surface: Surface;
  orgSlug?: string | null;
  /** The arm's own destinations. Capability destinations are added after them. */
  nav: NavItem[];
  title: string;
  children: ReactNode;
}

/**
 * The frame every surface shares.
 *
 * It sets `data-surface`, which is the whole of the visual difference between
 * the arms — the primitives read their colours from the custom properties that
 * attribute selects, so nothing below here branches on which arm it is in.
 *
 * It also decides the navigation once, from the arm's own items plus whatever
 * `capabilitiesFor` says this surface mounts. That list is then handed to the
 * help panel, which is how the assistant can say "open Study material" on an
 * institution screen without anybody scripting it.
 */
export function SurfaceShell({ surface, orgSlug = null, nav, title, children }: SurfaceShellProps) {
  return (
    <RequireSession>
      <SurfaceProvider surface={surface} orgSlug={orgSlug}>
        <Frame surface={surface} orgSlug={orgSlug} nav={nav} title={title}>
          {children}
        </Frame>
      </SurfaceProvider>
    </RequireSession>
  );
}

function Frame({ surface, orgSlug, nav, title, children }: Omit<SurfaceShellProps, "children"> & { children: ReactNode }) {
  const { session, signOut } = useSession();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const items = useMemo<NavItem[]>(() => {
    const mounted = capabilitiesFor(surface, {
      can: session?.capabilities.can ?? {},
      orgSlug,
    }).map((capability) => ({
      key: capability.id,
      label: capability.title,
      href: capability.href,
      icon: capability.icon,
    }));
    return [...nav, ...mounted];
  }, [surface, session?.capabilities.can, orgSlug, nav]);

  const helpNav = useMemo<HelpNavItem[]>(
    () => items.map((item) => ({ key: item.key, label: item.label, path: item.href })),
    [items],
  );

  return (
    <div data-surface={surface} className="flex min-h-screen bg-canvas text-ink">
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
        <div className="flex h-14 items-center justify-between border-b border-border px-4">
          <span className="text-sm font-semibold text-ink">{title}</span>
          <button
            type="button"
            className="md:hidden"
            onClick={() => setMenuOpen(false)}
            aria-label="Close menu"
          >
            <LuX className="h-5 w-5 text-ink-muted" aria-hidden />
          </button>
        </div>

        <nav className="flex flex-col gap-0.5 p-3" aria-label={`${title} sections`}>
          {items.map((item) => {
            const active = pathname === item.href || pathname?.startsWith(`${item.href}/`);
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
          })}
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
  );
}
