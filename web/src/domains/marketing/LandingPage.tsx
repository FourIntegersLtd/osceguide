import { ExamCards } from "@/domains/marketing/home/ExamCards";
import { FeatureRows } from "@/domains/marketing/home/FeatureRows";
import { FoundersNote } from "@/domains/marketing/home/FoundersNote";
import { HomeFaq } from "@/domains/marketing/home/HomeFaq";
import { HomeFeedback } from "@/domains/marketing/home/HomeFeedback";
import { HomePricing } from "@/domains/marketing/home/HomePricing";
import { HowItWorks } from "@/domains/marketing/home/HowItWorks";
import { InstitutionsBand } from "@/domains/marketing/home/InstitutionsBand";
import { LandingHero } from "@/domains/marketing/home/LandingHero";
import { ProofStrip } from "@/domains/marketing/home/ProofStrip";
import { HomeTestimonials } from "@/domains/marketing/home/HomeVoices";
import { SiteShell } from "@/domains/marketing/site/SiteShell";

/** The public landing page at `/`. Server-rendered; the interactive parts are small client islands. */
export function LandingPage() {
  return (
    <SiteShell nav="landing">
      <LandingHero />
      <ProofStrip />
      <HowItWorks />
      <FeatureRows />
      <ExamCards />
      <HomeTestimonials />
      <HomePricing />
      <InstitutionsBand />
      <HomeFaq />
      <FoundersNote />
      <HomeFeedback />
    </SiteShell>
  );
}
