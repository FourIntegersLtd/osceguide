import { LuBell } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * The learner's notifications: notes from the OSCE Guide team, answers to reports and
 * messages, and announcements. Consumer arm only for now; mounting it on
 * institutions is adding `"assess"` here.
 */
export const inboxCapability: CapabilityModule = {
  id: "inbox",
  title: "Notifications",
  description: "Replies and news from the OSCE Guide team.",
  surfaces: ["train"],
  permission: null,
  path: "/notifications",
  icon: LuBell,
  section: "connect",
};
