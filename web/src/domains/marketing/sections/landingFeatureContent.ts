export type LandingFeatureItem = {
  title: string;
  description: string;
  href: string;
  icon: "simulation" | "colleagues" | "feedback";
};

export const CLASSIC_LANDING_FEATURES: LandingFeatureItem[] = [
  {
    icon: "simulation",
    title: "AI-Powered Simulations",
    description:
      "Realistic patients with high-stakes scenarios powered by advanced Voice AI technology",
    href: "#feedback",
  },
  {
    icon: "colleagues",
    title: "Practice with Colleagues",
    description:
      "Match instantly with colleagues or schedule a session that fits. Real-time video practice.",
    href: "#practice",
  },
  {
    icon: "feedback",
    title: "Examiner-Style Feedback",
    description:
      "Every station returns a domain breakdown, the marks you earned, and the exact moment in your transcript where each was decided.",
    href: "#feedback",
  },
];
