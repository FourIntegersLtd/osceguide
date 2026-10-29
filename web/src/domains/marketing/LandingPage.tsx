import { HomeExams, HomeFeatures } from "@/domains/marketing/home/HomeFeatures";
import { HomeFaq } from "@/domains/marketing/home/HomeFaq";
import { HomeFeedback } from "@/domains/marketing/home/HomeFeedback";
import { HomeHero } from "@/domains/marketing/home/HomeHero";
import { HomeNumbers } from "@/domains/marketing/home/HomeNumbers";
import { HomeNeurodiversity, HomePractice } from "@/domains/marketing/home/HomePractice";
import { HomePricing } from "@/domains/marketing/home/HomePricing";
import { HomeSteps } from "@/domains/marketing/home/HomeSteps";
import { HomeFounders, HomeTestimonials } from "@/domains/marketing/home/HomeVoices";
import { SiteShell } from "@/domains/marketing/site/SiteShell";

/** The public landing page at `/`. Server-rendered; the interactive parts are small client islands. */
export function LandingPage() {
  return (
    <SiteShell nav="landing">
      <HomeHero />
      <HomeSteps />
      <HomeNumbers />
      <HomeFeatures />
      <HomeExams />
      <HomePractice />
      <HomeNeurodiversity />
      <HomeFounders />
      <HomeTestimonials />
      <HomePricing />
      <HomeFaq />
      <HomeFeedback />
    </SiteShell>
  );
}
