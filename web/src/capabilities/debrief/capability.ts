import { LuMessageSquareQuote } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * Talking an attempt through afterwards.
 *
 * A debrief is a second conversation about a station already sat — what was
 * missed, what to do differently — and it is written against the same attempt,
 * so an institution reviewing a cohort's stations wants it for the same reason
 * a consumer does.
 *
 * Listed in the navigation under Practice, as well as reached from an attempt:
 * the list of every debrief the person has had is its own screen, and without
 * an entry it was only reachable from links.
 */
export const debriefCapability: CapabilityModule = {
  id: "debrief",
  title: "Debrief",
  description: "Work back through a station you have already sat.",
  surfaces: ["train", "assess"],
  permission: null,
  section: "practice",
  path: "/debriefs",
  icon: LuMessageSquareQuote,
};
