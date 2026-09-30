import type { ComponentType } from "react";
import type { LandingSectionKey } from "../landingConfig";
import { LandingExamsSection } from "../LandingExamsSection";
import { LandingFeaturesSection } from "./LandingFeaturesSection";
import { LandingFeedbackSection } from "./LandingFeedbackSection";
import { LandingFooterSection } from "./LandingFooterSection";
import { LandingHeroSection } from "./LandingHeroSection";
import { LandingFoundersSection } from "./LandingFoundersSection";
import { LandingNumbersSection } from "./LandingNumbersSection";
import { LandingNeurodiversitySection } from "./LandingNeurodiversitySection";
import { LandingPracticeSection } from "./LandingPracticeSection";
import { LandingPricingSection } from "./LandingPricingSection";
import { LandingFaqSection } from "./LandingFaqSection";
import { LandingTestimonialsSection } from "./LandingTestimonialsSection";

export const landingSectionRegistry: Record<
  LandingSectionKey,
  ComponentType
> = {
  hero: LandingHeroSection,
  numbers: LandingNumbersSection,
  features: LandingFeaturesSection,
  exams: LandingExamsSection,
  practice: LandingPracticeSection,
  neuro: LandingNeurodiversitySection,
  founders: LandingFoundersSection,
  faq: LandingFaqSection,
  pricing: LandingPricingSection,
  feedback: LandingFeedbackSection,
  testimonials: LandingTestimonialsSection,
  footer: LandingFooterSection,
};

export function LandingSection({ sectionKey }: { sectionKey: LandingSectionKey }) {
  const Component = landingSectionRegistry[sectionKey];
  return Component ? <Component /> : null;
}
