import { LuShield } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/** Staff console: recent community posts for moderation. */
export const staffModerationCapability: CapabilityModule = {
  id: "staff-moderation",
  title: "Moderation",
  description: "Review and remove community posts.",
  surfaces: ["platform"],
  permission: "administer_platform",
  path: "/moderation",
  icon: LuShield,
  section: "content",
};
