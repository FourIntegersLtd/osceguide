import { LuTrophy } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * A trainee's streaks and badges, computed from their own attempts.
 *
 * Mounted on `train` only — the legacy client carried it as a permanent
 * top-level sidebar item for consumers (`scaOnly: false`), and supervisors and
 * staff have no attempts-based record of their own. The component lives in the
 * account capability folder because it is about the person rather than the
 * practice tools, but it is a separate capability: Settings and Achievements
 * are different destinations.
 */
export const achievementsCapability: CapabilityModule = {
  id: "achievements",
  title: "Achievements",
  description: "Your streaks and badges.",
  surfaces: ["train"],
  permission: null,
  section: "general",
  path: "/achievements",
  icon: LuTrophy,
};
