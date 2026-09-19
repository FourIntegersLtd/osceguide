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
 * `hidden`: reached from an attempt, never from the navigation. There is no
 * useful list of "all my debriefs" that the attempt history does not answer
 * better.
 */
export const debriefCapability: CapabilityModule = {
  id: "debrief",
  title: "Debrief",
  description: "Work back through a station you have already sat.",
  surfaces: ["train", "assess"],
  permission: null,
  path: "/debriefs",
  icon: LuMessageSquareQuote,
  hidden: true,
};
