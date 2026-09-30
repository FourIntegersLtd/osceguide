"use client";

import { createContext, useContext, useMemo } from "react";
import type { ReactNode } from "react";
import type { Surface } from "@/capabilities/surface";

export interface SurfaceContextValue {
  surface: Surface;
  /** The organisation whose workspace this is, or null for a personal one. */
  orgSlug: string | null;
  /**
   * Everything this surface's screens hang off, e.g. `/app/me` or
   * `/app/kings`. Passed in by the shell rather than computed here: the
   * capabilities tier must not know the shape of the route tree.
   */
  basePath: string;
  /** Prefix a capability-relative path with the surface's base. */
  hrefFor: (path: string) => string;
}

const SurfaceContext = createContext<SurfaceContextValue | null>(null);

/**
 * Set once by a surface shell.
 *
 * This is the only thing a capability learns about where it is running, and it
 * is deliberately small: a name and a base path. Anything richer — the
 * organisation's settings, the trainee's cohort — would tempt a capability into
 * branching on the arm, which is the behaviour the tier exists to prevent.
 */
export function SurfaceProvider({
  surface,
  orgSlug = null,
  basePath,
  children,
}: {
  surface: Surface;
  orgSlug?: string | null;
  basePath: string;
  children: ReactNode;
}) {
  const value = useMemo<SurfaceContextValue>(
    () => ({ surface, orgSlug, basePath, hrefFor: (path: string) => `${basePath}${path}` }),
    [surface, orgSlug, basePath],
  );

  return <SurfaceContext.Provider value={value}>{children}</SurfaceContext.Provider>;
}

export function useSurface(): SurfaceContextValue {
  const ctx = useContext(SurfaceContext);
  if (!ctx) throw new Error("useSurface must be used within a SurfaceProvider");
  return ctx;
}

/** For capabilities that render outside a shell (an auth page, a share link). */
export function useOptionalSurface(): SurfaceContextValue | null {
  return useContext(SurfaceContext);
}
