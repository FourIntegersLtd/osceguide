import { LuMail } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * The learner's inbox: notes from the OSCE Guide team, answers to reports and
 * messages, and announcements. Consumer arm only for now; mounting it on
 * institutions is adding `"assess"` here.
 */
export const inboxCapability: CapabilityModule = {
  id: "inbox",
  title: "Inbox",
  description: "Messages and announcements from the OSCE Guide team.",
  surfaces: ["train"],
  permission: null,
  path: "/inbox",
  icon: LuMail,
  section: "connect",
};
