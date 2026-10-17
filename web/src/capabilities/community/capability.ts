import { LuUsers } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * Questions and answers.
 *
 * Consumer only. The backend's `audience` can scope a thread to one
 * organisation, but the institution arm does not mount the screens.
 */
export const communityCapability: CapabilityModule = {
  id: "community",
  title: "Community",
  description: "Ask the community a question, and answer other people's.",
  surfaces: ["train"],
  permission: null,
  section: "connect",
  path: "/discussion",
  icon: LuUsers,
};
