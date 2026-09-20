import { LuTrendingUp } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/** Staff console: partner attribution funnel and tracking links. */
export const staffGrowthCapability: CapabilityModule = {
  id: "staff-growth",
  title: "Growth",
  description: "Partner funnels, ref ids and reporter access.",
  surfaces: ["platform"],
  permission: "administer_platform",
  path: "/growth",
  icon: LuTrendingUp,
  section: "content",
};
