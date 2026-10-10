import { LuMessageSquare } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * Contact & Feedback — the retiring client's `/messages` in its sidebar,
 * between the study material and the community. It is a destination rather
 * than a dock, so unlike `help` it is not hidden; it is mounted only on the
 * consumer arm because that is where the old client had it.
 */
export const messagesCapability: CapabilityModule = {
  id: "messages",
  title: "Contact & Feedback",
  description: "Send a message or product feedback to the OSCE Guide team.",
  surfaces: ["train"],
  permission: null,
  path: "/messages",
  icon: LuMessageSquare,
  section: "connect",
};
