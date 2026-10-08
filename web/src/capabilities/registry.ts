import type { CapabilityModule, MountedCapability } from "@/capabilities/contract";
import type { Surface } from "@/capabilities/surface";
import { helpCapability } from "@/capabilities/help/capability";
import { inboxCapability } from "@/capabilities/inbox/capability";
import { messagesCapability } from "@/capabilities/help/messagesCapability";
import { mediaCapability } from "@/capabilities/media/capability";
import { STUDY_NAV_CAPABILITIES } from "@/capabilities/media/studyCapabilities";
import { stationsCapability } from "@/capabilities/stations/capability";
import { communityCapability } from "@/capabilities/community/capability";
import { peerPracticeCapability } from "@/capabilities/peer-practice/capability";
import { debriefCapability } from "@/capabilities/debrief/capability";
import { transcriptsCapability } from "@/capabilities/transcripts/capability";
import { accountCapability } from "@/capabilities/account/capability";
import { authoringCapability } from "@/capabilities/authoring/capability";
import { staffMediaCapability } from "@/capabilities/staff-media/capability";
import { staffGrowthCapability } from "@/capabilities/staff-growth/capability";
import { staffModerationCapability } from "@/capabilities/staff-moderation/capability";
import { achievementsCapability } from "@/capabilities/account/achievementsCapability";

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
  ...STUDY_NAV_CAPABILITIES,
  mediaCapability,
  inboxCapability,
  messagesCapability,
  communityCapability,
  peerPracticeCapability,
  debriefCapability,
  transcriptsCapability,
  accountCapability,
  achievementsCapability,
  staffMediaCapability,
  staffGrowthCapability,
  staffModerationCapability,
  // Last: the staff catalogue lists Authoring after Study material and Moderation.
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
  /**
   * The person's exam, for capabilities that name the exams they serve.
   * Left out, no capability is filtered by exam — route guards want that.
   */
  examCode?: string | null;
}

/**
 * The capabilities a surface shows, with their hrefs resolved.
 *
 * Gating is the backend's answer, never a role read in the browser.
 */
export function capabilitiesFor(
  surface: Surface,
  { can = {}, basePath = "", includeHidden = false, examCode }: MountOptions = {},
): MountedCapability[] {
  return CAPABILITIES.filter((capability) => {
    if (!capability.surfaces.includes(surface)) return false;
    if (capability.hidden && !includeHidden) return false;
    const staff = can.run_circuits === true;
    if (staff && capability.staffRefusedOn?.includes(surface)) return false;
    if (!includeHidden && staff && capability.staffNavHiddenOn?.includes(surface)) return false;
    if (!permitted(capability.permission, can)) return false;
    if (examCode !== undefined && capability.exams && !capability.exams.includes(examCode ?? "")) {
      return false;
    }
    return true;
  }).map((capability) => ({ ...capability, href: `${basePath}${capability.path}` }));
}

/**
 * Whether the backend grants what this capability needs.
 *
 * A list is satisfied by any one of its entries. Nothing is satisfied by
 * everyone signed in — the API still decides per item, and hiding a whole
 * section would also hide the parts a person may use.
 */
function permitted(
  permission: CapabilityModule["permission"],
  can: Record<string, boolean>,
): boolean {
  if (!permission) return true;
  const needed = Array.isArray(permission) ? permission : [permission];
  return needed.some((p) => can[p] === true);
}

export function capabilityById(id: string): CapabilityModule | undefined {
  return CAPABILITIES.find((capability) => capability.id === id);
}
