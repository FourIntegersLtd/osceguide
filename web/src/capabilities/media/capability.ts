import { LuLibrary } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * Study material: decks, summaries, articles and episodes.
 *
 * Mounted on Train and Assess. This one line is the whole of "institutions
 * want the slides too" — the screens were written against the surface context
 * rather than a consumer layout, so there was nothing to port.
 *
 * No permission: the API decides per item what a person may read, and hiding
 * the whole section would also hide the free material.
 */
export const mediaCapability: CapabilityModule = {
  id: "media",
  title: "Study material",
  description: "Slide decks, summaries, articles and podcast episodes.",
  surfaces: ["train", "assess"],
  permission: null,
  path: "/library",
  icon: LuLibrary,
};
