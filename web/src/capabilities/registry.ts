import type { CapabilityModule, MountedCapability } from "@/capabilities/contract";
import type { Surface } from "@/capabilities/surface";
import { helpCapability } from "@/capabilities/help/capability";
import { mediaCapability } from "@/capabilities/media/capability";
import { stationsCapability } from "@/capabilities/stations/capability";
import { communityCapability } from "@/capabilities/community/capability";
import { peerPracticeCapability } from "@/capabilities/peer-practice/capability";
import { debriefCapability } from "@/capabilities/debrief/capability";
import { transcriptsCapability } from "@/capabilities/transcripts/capability";
import { accountCapability } from "@/capabilities/account/capability";
import { authoringCapability } from "@/capabilities/authoring/capability";

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
  peerPracticeCapability,
  debriefCapability,
  transcriptsCapability,
  accountCapability,
  authoringCapability,
];

export interface MountOptions {
  /** From `/me/capabilities`. A capability with a permission is hidden without it. */
  can?: Record<string, boolean>;
  /**
   * What the surface's hrefs hang off, e.g. `/app/kings`. The shell knows it;
   * this tier must not, or a capability could reconstruct the route tree.
   */
  basePath?: string;
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
  { can = {}, basePath = "", includeHidden = false }: MountOptions = {},
): MountedCapability[] {
  return CAPABILITIES.filter((capability) => {
    if (!capability.surfaces.includes(surface)) return false;
    if (capability.hidden && !includeHidden) return false;
    if (capability.permission && can[capability.permission] !== true) return false;
    return true;
  }).map((capability) => ({ ...capability, href: `${basePath}${capability.path}` }));
}

export function capabilityById(id: string): CapabilityModule | undefined {
  return CAPABILITIES.find((capability) => capability.id === id);
}
