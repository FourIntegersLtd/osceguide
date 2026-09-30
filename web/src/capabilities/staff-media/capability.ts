import { LuBookOpen } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/** Staff console: create and publish study material for every exam. */
export const staffMediaCapability: CapabilityModule = {
  id: "staff-media",
  title: "Study material",
  description: "Summaries, decks, articles and podcast episodes.",
  surfaces: ["platform"],
  permission: "administer_platform",
  path: "/media",
  icon: LuBookOpen,
  section: "catalogue",
};
