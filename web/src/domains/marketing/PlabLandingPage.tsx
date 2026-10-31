import { HiOutlineClipboardDocumentCheck, HiOutlineClipboardDocumentList, HiOutlineHeart, HiOutlineNumberedList } from "react-icons/hi2";
import { ExamBlogRail } from "@/capabilities/media";
import { CardGrid, TitledSection } from "@/domains/marketing/home/Blocks";
import { ExamHero } from "@/domains/marketing/exam/ExamHero";
import { HomeFaq } from "@/domains/marketing/home/HomeFaq";
import { HomeNeurodiversity, HomePractice } from "@/domains/marketing/home/HomePractice";
import { HomeFounders } from "@/domains/marketing/home/HomeVoices";
import { LandingPricingSection } from "@/domains/marketing/Pricing";
import { LandingSimulationShowcase } from "@/domains/marketing/showcases/LandingSimulationShowcase";
import { SiteShell } from "@/domains/marketing/site/SiteShell";

const plabHighlights = [
  { Icon: HiOutlineNumberedList, title: "Structured Approach", body: "Follow a systematic approach to clinical management." },
  { Icon: HiOutlineClipboardDocumentCheck, title: "Evidence-Based Management", body: "Access evidence-based management plans." },
  { Icon: HiOutlineHeart, title: "Holistic Care Planning", body: "Address both clinical and psychosocial aspects of patient care." },
];

const stationTypes = [
  { title: "Acute care & resuscitation", body: "Run A–E assessments for sepsis, trauma, anaphylaxis, and other emergencies under pressure." },
  { title: "History & examination", body: "Practice focused history taking and examination." },
  { title: "Ethics & communication", body: "Build confidence tackling safeguarding, consent, and breaking-bad-news scenarios." },
];

const preparationWorkflow = [
  { Icon: HiOutlineClipboardDocumentList, title: "Discover", body: "Bench yourself against 100+ PLAB 2 stations carefully curated by practicing doctors." },
  { Icon: HiOutlineClipboardDocumentList, title: "Diagnose", body: "Unlock granular analytics on timing, rapport, differential reasoning, and management after each session." },
  { Icon: HiOutlineClipboardDocumentList, title: "Deliver", body: "Debrief with our custom AI tutor, Athena, who guides you through communication and management outlines until you're exam ready." },
];

export default function PlabLandingPage() {
  return (
    <SiteShell exam="plab">
      <ExamHero
        exam="plab"
        title={
          <>
            <span className="block">Pass the PLAB 2 exam with</span>
            <span className="block text-site-brand">voice-first AI practice</span>
          </>
        }
        lead="Sharpen your data gathering, interpersonal skills, and management under timed pressure, so you arrive in Manchester confident, fluent, and examiner-ready."
      />

      <HomeFounders />

      <TitledSection
        tone="card"
        title="Talk through the management, out loud"
        sub="Structured, evidence-based plans that cover both clinical and psychosocial care, and an AI patient to rehearse them on, marked as you speak."
      >
        <CardGrid items={plabHighlights} />
        <LandingSimulationShowcase variant="plab" />
      </TitledSection>

      <TitledSection title="Nail every PLAB 2 station type" sub="Train with voice simulations that replicate the 16-station circuit.">
        <CardGrid items={stationTypes} />
      </TitledSection>

      <TitledSection tone="card" title="The fastest loop from practice to pass" sub="High-yield PLAB stations and actionable analytics that elevate every practice session.">
        <CardGrid items={preparationWorkflow} />
      </TitledSection>

      <HomePractice
        eyebrow=""
        title="Practice with Colleagues"
      />
      <HomeNeurodiversity />
      <LandingPricingSection appType="plab" />
      <HomeFaq openFirst />
      <ExamBlogRail examCode="plab" />
    </SiteShell>
  );
}
