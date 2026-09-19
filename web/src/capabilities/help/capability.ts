import { LuCircleHelp } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * Ask for help by voice, wherever you are.
 *
 * Mounted on all four surfaces. The panel sends the surface and the shell's
 * own navigation labels with the session, so the same component answers an
 * institution admin's question about sittings and a candidate's about mocks —
 * the difference comes from the backend's content packs, not from a fork here.
 *
 * `hidden` because help is a docked panel on every screen rather than a
 * destination in the nav.
 */
export const helpCapability: CapabilityModule = {
  id: "help",
  title: "Help",
  description: "Ask a question by voice and get answers about this product.",
  surfaces: ["train", "assess", "hire", "platform"],
  permission: null,
  path: "/help",
  icon: LuCircleHelp,
  hidden: true,
};
