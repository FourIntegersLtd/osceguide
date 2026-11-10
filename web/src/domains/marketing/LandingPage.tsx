import { ExamCards } from "@/domains/marketing/home/ExamCards";
import { ClosingBand } from "@/domains/marketing/home/ClosingBand";
import { FeaturePanels } from "@/domains/marketing/home/FeaturePanels";
import { HowItWorks } from "@/domains/marketing/home/HowItWorks";
import { HomeFaq } from "@/domains/marketing/home/HomeFaq";
import { InstitutionsBand } from "@/domains/marketing/home/InstitutionsBand";
import { LandingHero } from "@/domains/marketing/home/LandingHero";
import { HomeTestimonials } from "@/domains/marketing/home/HomeVoices";
import { PricingSectionContent } from "@/domains/marketing/Pricing";
import { SiteShell } from "@/domains/marketing/site/SiteShell";

/** The public landing page at `/`. Server-rendered; the interactive parts are small client islands. */
export function LandingPage() {
  return (
    <SiteShell nav="landing" footer="light">
      <LandingHero />
      <HowItWorks />
      <FeaturePanels />
      <ExamCards />
      <PricingSectionContent section={{ tone: "card", pad: "py-16 md:py-24" }} />
      <HomeTestimonials tone="ground" ctas={null} />
      <InstitutionsBand />
      <HomeFaq />
      <ClosingBand />
    </SiteShell>
  );
}
