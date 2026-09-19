import type { CapabilityModule, MountedCapability } from "@/capabilities/contract";
import { surfaceBasePath, type Surface } from "@/capabilities/surface";
import { helpCapability } from "@/capabilities/help/capability";
import { mediaCapability } from "@/capabilities/media/capability";
import { stationsCapability } from "@/capabilities/stations/capability";
import { communityCapability } from "@/capabilities/community/capability";

/**
 * Every capability, and the surfaces each is mounted on.
 *
 * This list is the answer to "can institutions have the help section, the
 * slides and the summaries?". Today `help` and `media` are mounted on `train`
 * and `assess`, which is the whole of that feature request: the components
 * were written against the surface context rather than a consumer layout, so
 * mounting them elsewhere cost a line here and a route file.
 */
export const CAPABILITIES: readonly CapabilityModule[] = [
  stationsCapability,
  helpCapability,
  mediaCapability,
  communityCapability,
];

export interface MountOptions {
  /** From `/me/capabilities`. A capability with a permission is hidden without it. */
  can?: Record<string, boolean>;
  orgSlug?: string | null;
  /** Include capabilities marked `hidden`. Off by default; nav does not want them. */
  includeHidden?: boolean;
}

/**
 * The capabilities a surface shows, with their hrefs resolved.
 *
 * Gating is the backend's answer, never a role read in the browser.
 */
export function capabilitiesFor(
  surface: Surface,
  { can = {}, orgSlug = null, includeHidden = false }: MountOptions = {},
): MountedCapability[] {
  const base = surfaceBasePath(surface, orgSlug);
  return CAPABILITIES.filter((capability) => {
    if (!capability.surfaces.includes(surface)) return false;
    if (capability.hidden && !includeHidden) return false;
    if (capability.permission && can[capability.permission] !== true) return false;
    return true;
  }).map((capability) => ({ ...capability, href: `${base}${capability.path}` }));
}

export function capabilityById(id: string): CapabilityModule | undefined {
  return CAPABILITIES.find((capability) => capability.id === id);
}
