"use client";

import { HiOutlineClipboardDocumentCheck, HiOutlineClipboardDocumentList, HiOutlineHeart, HiOutlineNumberedList } from "react-icons/hi2";
import { FAQSection } from "./FAQ";
import { LandingFooter } from "./LandingFooter";
import { PracticeWithColleaguesSection } from "./PracticeWithColleagues";
import { NeurodiversitySupportSection } from "./NeurodiversitySupportSection";
import { LandingPricingSection } from "./Pricing";
import FoundersMessage from "./FoundersMessage";
import { ExamLandingShell } from "./ExamLandingShell";
import { ExamLandingHero } from "./ExamLandingHero";
import { LandingIconBadge } from "./LandingIconBadge";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { LandingSimulationShowcase } from "./showcases/LandingSimulationShowcase";
import { useLandingVariant } from "./LandingVariantContext";
import type { LandingIconColor } from "./landingIconPalette";

const plabHighlights: Array<{
  icon: typeof HiOutlineNumberedList;
  color: LandingIconColor;
  title: string;
  description: string;
}> = [
  {
    icon: HiOutlineNumberedList,
    color: "blue",
    title: "Structured Approach",
    description: "Follow a systematic approach to clinical management.",
  },
  {
    icon: HiOutlineClipboardDocumentCheck,
    color: "indigo",
    title: "Evidence-Based Management",
    description: "Access evidence-based management plans.",
  },
  {
    icon: HiOutlineHeart,
    color: "violet",
    title: "Holistic Care Planning",
    description:
      "Address both clinical and psychosocial aspects of patient care.",
  },
];

const stationTypes = [
  {
    title: "Acute care & resuscitation",
    description:
      "Run A–E assessments for sepsis, trauma, anaphylaxis, and other emergencies under pressure.",
  },
  {
    title: "History & examination",
    description: "Practice focused history taking and examination.",
  },
  {
    title: "Ethics & communication",
    description:
      "Build confidence tackling safeguarding, consent, and breaking-bad-news scenarios.",
  },
];

const preparationWorkflow = [
  {
    title: "Discover",
    description:
      "Bench yourself against 100+ PLAB 2 stations carefully curated by practicing doctors.",
  },
  {
    title: "Diagnose",
    description:
      "Unlock granular analytics on timing, rapport, differential reasoning, and management after each session.",
  },
  {
    title: "Deliver",
    description:
      "Debrief with our custom AI tutor, Athena, who guides you through communication and management outlines until you're exam ready.",
  },
];

function PlabLandingContent() {
  const { type } = useLandingVariant();

  return (
    <>
      <ExamLandingHero
        appType="plab"
        title={
          <>
            <span className="block">Pass the PLAB 2 exam with</span>
            <span className="block text-osce-accent">voice-first AI practice</span>
          </>
        }
        lead="Sharpen your data gathering, interpersonal skills, and management under timed pressure, so you arrive in Manchester confident, fluent, and examiner-ready."
      />

      <FoundersMessage />

      <section
        className={`scroll-mt-20 ${landingSectionSurfaces.plain} ${type.sectionPaddingCompact}`}
      >
        <div className={`${type.sectionShell} space-y-12 sm:space-y-16`}>
          <div className="text-center">
            <h2 className={type.sectionTitle}>
              Talk through the management, out loud
            </h2>
            <p className={type.sectionSubtitleCentered}>
              Structured, evidence-based plans that cover both clinical and
              psychosocial care, and an AI patient to rehearse them on, marked
              as you speak.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3 sm:gap-10">
            {plabHighlights.map((item) => (
              <div key={item.title}>
                <LandingIconBadge icon={item.icon} color={item.color} size="sm" />
                <h3 className={`mt-4 ${type.itemTitle}`}>{item.title}</h3>
                <p className={`mt-2 ${type.itemBody}`}>{item.description}</p>
              </div>
            ))}
          </div>
          <LandingSimulationShowcase variant="plab" />
        </div>
      </section>

      <section
        className={`scroll-mt-20 ${landingSectionSurfaces.features} ${type.sectionPadding}`}
      >
        <div className={type.sectionShell}>
          <div className="text-center">
            <h2 className={type.sectionTitle}>Nail every PLAB 2 station type</h2>
            <p className={type.sectionSubtitleCentered}>
              Train with voice simulations that replicate the 16-station
              circuit.
            </p>
          </div>
          <div className="mt-12 grid grid-cols-1 gap-8 sm:mt-16 sm:grid-cols-2 lg:grid-cols-3 lg:gap-10">
            {stationTypes.map((station) => (
              <div key={station.title} className="space-y-2">
                <h3 className={type.itemTitle}>{station.title}</h3>
                <p className={type.itemBody}>{station.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section
        className={`scroll-mt-20 ${landingSectionSurfaces.exams} ${type.sectionPadding}`}
      >
        <div className={type.sectionShell}>
          <div className="text-center">
            <h2 className={type.sectionTitle}>
              The fastest loop from practice to pass
            </h2>
            <p className={type.sectionSubtitleCentered}>
              High-yield PLAB stations and actionable analytics that elevate
              every practice session.
            </p>
          </div>
          <div className="mt-12 grid grid-cols-1 gap-6 sm:gap-8 lg:grid-cols-3">
            {preparationWorkflow.map((step, index) => (
              <div key={step.title} className={type.featureCard}>
                <LandingIconBadge
                  icon={HiOutlineClipboardDocumentList}
                  color={index === 0 ? "blue" : index === 1 ? "indigo" : "cyan"}
                  size="sm"
                />
                <h3 className={`mt-4 ${type.itemTitle}`}>{step.title}</h3>
                <p className={`mt-3 ${type.itemBody}`}>{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <PracticeWithColleaguesSection />
      <NeurodiversitySupportSection />
      <LandingPricingSection appType="plab" />
      <FAQSection />
      <LandingFooter sectionLinkPrefix="/" />
    </>
  );
}

export default function PlabLandingPage() {
  return (
    <ExamLandingShell appType="plab">
      <PlabLandingContent />
    </ExamLandingShell>
  );
}
