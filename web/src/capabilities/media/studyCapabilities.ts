import { HiOutlineNewspaper, HiOutlinePlayCircle } from "react-icons/hi2";
import { GiSpellBook } from "react-icons/gi";
import { LuPodcast } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

const SURFACES = ["train", "assess"] as const;

/**
 * Study material as separate nav items, matching the retiring B2C sidebar
 * (A to Z, Slides, …) rather than one combined library screen.
 */
export const studyAToZCapability: CapabilityModule = {
  id: "study-a-to-z",
  title: "A to Z",
  description: "Condition summaries from A to Z and by specialty.",
  surfaces: SURFACES,
  permission: null,
  section: "practice",
  path: "/summary",
  icon: GiSpellBook,
};

export const studySlidesCapability: CapabilityModule = {
  id: "study-slides",
  title: "Slides",
  description: "Video presentations by topic.",
  surfaces: SURFACES,
  permission: null,
  section: "practice",
  path: "/slides",
  icon: HiOutlinePlayCircle,
};

export const studyPodcastCapability: CapabilityModule = {
  id: "study-podcast",
  title: "Podcast",
  description: "Podcast episodes to listen between stations.",
  surfaces: SURFACES,
  permission: null,
  section: "practice",
  path: "/podcast",
  icon: LuPodcast,
};

export const studyArticlesCapability: CapabilityModule = {
  id: "study-articles",
  title: "Articles",
  description: "Articles and blog posts from the study library.",
  surfaces: SURFACES,
  permission: null,
  section: "practice",
  path: "/articles",
  icon: HiOutlineNewspaper,
};

export const STUDY_NAV_CAPABILITIES: readonly CapabilityModule[] = [
  studyAToZCapability,
  studySlidesCapability,
  studyPodcastCapability,
  studyArticlesCapability,
];
