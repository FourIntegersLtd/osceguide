import type { ComponentType } from "react";
import type { Permission } from "@/foundation/session";
import type { Surface } from "@/capabilities/surface";
import type { NavSection } from "@/capabilities/navSection";

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
   *
   * A list means *any of them* will do, which is not a loophole but the honest
   * shape of a capability that two different kinds of person reach: authoring
   * is `read_org` for somebody inside an organisation and
   * `administer_platform` for OSCE Guide's own staff, who belong to no
   * organisation and would otherwise fail an org permission for the platform
   * catalogue they own.
   * `null` means everyone signed in may use it — study material and help are
   * like this, and entitlement is enforced per item by the API rather than by
   * hiding the section.
   */
  permission: Permission | readonly Permission[] | null;
  /** Path under the surface's base, e.g. `/help`. */
  path: string;
  /** Rendered by the route file that mounts it. */
  icon?: ComponentType<{ className?: string }>;
  /** Left out of surface navigation; reachable by direct link only. */
  hidden?: boolean;
  /**
   * Which navigation group it sits in on the arms that show groups.
   *
   * A capability names its own because the grouping is about what the thing
   * *is* — study material is practice, discussion is people — and an arm
   * listing them all over again would be the same knowledge in two places.
   */
  section?: NavSection;
  /**
   * The exams whose candidates see it in navigation, by exam code.
   *
   * Left out, every exam does. The marketplace is `["sca"]` because only SCA
   * candidates rehearse with a colleague — the retiring nav's `scaOnly`. It
   * only hides the nav entry: a direct link still opens the screen, as it did.
   */
  exams?: readonly string[];
  /**
   * Where an arm that does not mount this capability goes instead of a 404 (a path inside
   * the workspace). Stations is `/mocks` on the trainee arm, which practises from mocks.
   */
  unmountedGoesTo?: string;
  /**
   * Arms where somebody who runs circuits is refused the page, by link as well as in
   * navigation (the trainee's study items and community, which staff have no use for).
   */
  staffRefusedOn?: readonly Surface[];
  /**
   * Arms where somebody who runs circuits does not see it in navigation, though the page stays
   * open: Authoring, where the arm lists its own Build entry that opens the same page.
   */
  staffNavHiddenOn?: readonly Surface[];
}

export interface MountedCapability extends CapabilityModule {
  /** The capability's path with the surface's base applied. */
  href: string;
}
