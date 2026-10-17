import { LuLibrary } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * Study material: decks, summaries, articles and episodes.
 *
 * Consumer only: institutions do not mount study material.
 *
 * No permission: the API decides per item what a person may read, and hiding
 * the whole section would also hide the free material.
 */
export const mediaCapability: CapabilityModule = {
  id: "media",
  title: "Study material",
  description: "Slide decks, summaries, articles and podcast episodes.",
  surfaces: ["train"],
  permission: null,
  section: "practice",
  path: "/library",
  icon: LuLibrary,
  /** Detail pages only; study kinds have their own nav entries. */
  hidden: true,
};
