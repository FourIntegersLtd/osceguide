import { SUPPORT_EMAIL } from "@/foundation/support";
import { ExamCards } from "@/domains/marketing/home/ExamCards";
import { FeatureRows } from "@/domains/marketing/home/FeatureRows";
import { FinalCta } from "@/domains/marketing/home/FinalCta";
import { FoundersNote } from "@/domains/marketing/home/FoundersNote";
import { HomeFaq } from "@/domains/marketing/home/HomeFaq";
import { HomeFeedback } from "@/domains/marketing/home/HomeFeedback";
import { HomePricing } from "@/domains/marketing/home/HomePricing";
import { HowItWorks } from "@/domains/marketing/home/HowItWorks";
import { InstitutionsBand } from "@/domains/marketing/home/InstitutionsBand";
import { LandingHero } from "@/domains/marketing/home/LandingHero";
import { ProofStrip } from "@/domains/marketing/home/ProofStrip";
import { TestimonialGrid } from "@/domains/marketing/home/TestimonialGrid";
import { FAQ_HEAD } from "@/domains/marketing/landingCopy";
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
      <TestimonialGrid />
      <HomePricing />
      <InstitutionsBand />
      <HomeFaq head={{ eyebrow: FAQ_HEAD.eyebrow, title: FAQ_HEAD.title, sub: <>{FAQ_HEAD.sub} <a href={`mailto:${SUPPORT_EMAIL}`} className="font-semibold text-site-brand underline-offset-4 hover:underline">{SUPPORT_EMAIL}</a>. {FAQ_HEAD.subTail}</> }} />
      <FoundersNote />
      <FinalCta />
      <HomeFeedback />
    </SiteShell>
  );
}
