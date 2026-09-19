"use client";

import { createContext, useContext, useMemo } from "react";
import type { ReactNode } from "react";
import { surfaceBasePath, type Surface } from "@/capabilities/surface";

export interface SurfaceContextValue {
  surface: Surface;
  /** The organisation whose workspace this is, when the surface has one. */
  orgSlug: string | null;
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
  children,
}: {
  surface: Surface;
  orgSlug?: string | null;
  children: ReactNode;
}) {
  const value = useMemo<SurfaceContextValue>(() => {
    const base = surfaceBasePath(surface, orgSlug);
    return { surface, orgSlug, hrefFor: (path: string) => `${base}${path}` };
  }, [surface, orgSlug]);

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
