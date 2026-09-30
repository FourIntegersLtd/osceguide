import { LuSparkles } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * Athena's introduction: who she is, and one scored exchange to show what she
 * does with a consultation.
 *
 * Hidden from navigation because it is something a person is *sent* to once,
 * from an empty dashboard or from account settings to watch again — a
 * permanent nav entry for a walkthrough is clutter for everybody who has
 * already seen it. It is a capability rather than a consumer screen because
 * the scenes come from the exam's content pack, which an institution's exam
 * has as much as a consumer's.
 */
export const onboardingCapability: CapabilityModule = {
  id: "onboarding",
  title: "Meet Athena",
  description: "A short introduction to Athena, and a demo consultation.",
  surfaces: ["train"],
  permission: null,
  path: "/onboarding",
  icon: LuSparkles,
  hidden: true,
};
