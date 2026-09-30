import type { LandingIconColor } from "../landingIconPalette";

export type LandingProductRailItem = {
  id: string;
  title: string;
  description: string;
  href: string;
  visual: "voice" | "marketplace" | "feedback" | "athena";
  color: LandingIconColor;
};

export const LANDING_PRODUCT_RAIL: LandingProductRailItem[] = [
  {
    id: "voice",
    title: "Voice stations",
    description:
      "Realistic patients with high-stakes scenarios powered by advanced Voice AI technology.",
    href: "#feedback",
    visual: "voice",
    color: "cyan",
  },
  {
    id: "marketplace",
    title: "Marketplace sessions",
    description:
      "Match instantly with colleagues or schedule a session that fits. Real-time video practice.",
    href: "#practice",
    visual: "marketplace",
    color: "green",
  },
  {
    id: "feedback",
    title: "Domain feedback",
    description:
      "Instant feedback based on the exam grading domains, with the moment each mark was decided.",
    href: "#feedback",
    visual: "feedback",
    color: "indigo",
  },
  {
    id: "athena",
    title: "Debrief with Athena",
    description:
      "Your AI tutor after every case, walking through communication and management outlines.",
    href: "#feedback",
    visual: "athena",
    color: "violet",
  },
];

export type ProductRailVisualProps = {
  item: LandingProductRailItem;
};
