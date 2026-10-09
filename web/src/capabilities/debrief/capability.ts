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
 * `hidden`: reached from an attempt (the station's Debriefs tab), never from
 * the navigation, so it stays inside practice rather than reading as a section
 * of its own. The list of every debrief stays open by link.
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
  hidden: true,
};
