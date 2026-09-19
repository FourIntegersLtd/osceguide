import { LuMessagesSquare } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * Questions and answers.
 *
 * Mounted on Train and Assess. The backend's `audience` scopes a thread to
 * everyone, to one organisation or to one group, so an institution gets a
 * private cohort discussion from these same screens.
 */
export const communityCapability: CapabilityModule = {
  id: "community",
  title: "Discussion",
  description: "Ask the community a question, and answer other people's.",
  surfaces: ["train", "assess"],
  permission: null,
  path: "/discussion",
  icon: LuMessagesSquare,
};
