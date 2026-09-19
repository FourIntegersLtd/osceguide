import type { ComponentType } from "react";
import type { Permission } from "@/foundation/session";
import type { Surface } from "@/capabilities/surface";

/**
 * What a capability is.
 *
 * A capability is a feature that belongs to no arm: the help section, the
 * study material, the station library, the attempt runner, the feedback
 * renderer. It is mountable on any surface that lists it, and it never learns
 * which one it is on except through `SurfaceContext`.
 *
 * The lint rule in `eslint.config.mjs` is what keeps this true: a capability
 * that imports a domain or a surface fails the build. That is deliberate — the
 * help section became consumer-only in the old client for exactly that reason,
 * one import at a time, and no rule caught it.
 *
 * Adding help to institutions is therefore adding `"assess"` to `surfaces`
 * below and dropping a three-line route file in. It is not a port.
 */
export interface CapabilityModule {
  /** Stable key. Used in nav, in tests, and as the React key. */
  id: string;
  /** Nav label. */
  title: string;
  /** One line, for nav tooltips and empty states. */
  description: string;
  /** The arms this capability may be mounted on. */
  surfaces: readonly Surface[];
  /**
   * The backend permission that gates it, checked against `/me/capabilities`.
   * `null` means everyone signed in may use it — study material and help are
   * like this, and entitlement is enforced per item by the API rather than by
   * hiding the section.
   */
  permission: Permission | null;
  /** Path under the surface's base, e.g. `/help`. */
  path: string;
  /** Rendered by the route file that mounts it. */
  icon?: ComponentType<{ className?: string }>;
  /** Left out of surface navigation; reachable by direct link only. */
  hidden?: boolean;
}

export interface MountedCapability extends CapabilityModule {
  /** The capability's path with the surface's base applied. */
  href: string;
}
