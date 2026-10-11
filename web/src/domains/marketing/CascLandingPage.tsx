"use client";

import {
  HiOutlineChatBubbleLeftRight,
  HiOutlineClipboardDocumentList,
  HiOutlineScale,
  HiOutlineShieldCheck,
} from "react-icons/hi2";
import { FAQSection } from "./FAQ";
import { ExamBlogRail } from "@/capabilities/media";
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
import { LandingProgressShowcase } from "./showcases/LandingProgressShowcase";
import { useLandingVariant } from "./LandingVariantContext";
import type { LandingIconColor } from "./landingIconPalette";

/** The three skills a CASC examiner is looking for in almost every station. */
const cascHighlights: Array<{
  icon: typeof HiOutlineShieldCheck;
  color: LandingIconColor;
  title: string;
  description: string;
}> = [
  {
    icon: HiOutlineShieldCheck,
    color: "blue",
    title: "Risk, asked out loud",
    description:
      "Rehearse the direct, sensitive questions about suicide, self-harm, harm to others and self-neglect until they come naturally.",
  },
  {
    icon: HiOutlineScale,
    color: "indigo",
    title: "Mental state and capacity",
    description:
      "Work through a systematic mental state examination and a Mental Capacity Act assessment against the clock.",
  },
  {
    icon: HiOutlineChatBubbleLeftRight,
    color: "violet",
    title: "Explaining and negotiating",
    description:
      "Explain diagnoses and treatments to patients, relatives and colleagues in plain, non-stigmatising language.",
  },
];

/** The CASC's three station families, as the college groups them. */
const stationTypes = [
  {
    title: "History taking & risk",
    description:
      "Focused psychiatric histories across general adult, old age, CAMHS, perinatal, substance misuse and forensic presentations, with the risk assessment built in.",
  },
  {
    title: "Examination",
    description:
      "Mental state, cognitive and targeted physical examinations, plus capacity assessments, each marked on what the task asked of you.",
  },
  {
    title: "Management & communication",
    description:
      "Discuss a plan with a worried relative, explain medication such as lithium or clozapine, or hand over to a colleague, using the Mental Health Act where it applies.",
  },
];

/** The shape of the day, so a candidate knows what they are rehearsing for. */
const examFormat = [
  { value: "16", label: "stations across two circuits on one day" },
  { value: "7 min", label: "per station, with the role player" },
  { value: "4 min / 90 s", label: "reading time in the morning and afternoon circuits" },
];

const preparationWorkflow = [
  {
    title: "Discover",
    description:
      "Practise CASC-style stations written by psychiatrists, with role players who respond to your tone as well as your questions.",
  },
  {
    title: "Diagnose",
    description:
      "See every station marked across history, examination, management and communication, with quotes from your own transcript.",
  },
  {
    title: "Deliver",
    description:
      "Debrief with Athena, our AI tutor, on the risk questions you missed and the explanation you could make clearer, then run the station again.",
  },
];

function CascLandingContent() {
  const { type } = useLandingVariant();

  return (
    <>
      <ExamLandingHero
        appType="casc"
        title={
          <>
            <span className="block">Pass the MRCPsych CASC with</span>
            <span className="block text-osce-accent">voice-first AI practice</span>
          </>
        }
        lead="Rehearse risk assessments, mental state examinations and difficult conversations with an AI role player, marked as you speak, so you walk into all 16 stations calm and fluent."
      />

      <FoundersMessage />

      <section
        className={`scroll-mt-20 ${landingSectionSurfaces.plain} ${type.sectionPaddingCompact}`}
      >
        <div className={`${type.sectionShell} space-y-12 sm:space-y-16`}>
          <div className="text-center">
            <h2 className={type.sectionTitle}>Seven minutes, one task, out loud</h2>
            <p className={type.sectionSubtitleCentered}>
              CASC stations reward the doctor who completes the task safely and
              empathically. Practise saying it, not just knowing it.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3 sm:gap-10">
            {cascHighlights.map((item) => (
              <div key={item.title}>
                <LandingIconBadge icon={item.icon} color={item.color} size="sm" />
                <h3 className={`mt-4 ${type.itemTitle}`}>{item.title}</h3>
                <p className={`mt-2 ${type.itemBody}`}>{item.description}</p>
              </div>
            ))}
          </div>
          <LandingSimulationShowcase variant="casc" />
        </div>
      </section>

      <section
        className={`scroll-mt-20 ${landingSectionSurfaces.features} ${type.sectionPadding}`}
      >
        <div className={type.sectionShell}>
          <div className="text-center">
            <h2 className={type.sectionTitle}>Nail every CASC station type</h2>
            <p className={type.sectionSubtitleCentered}>
              Voice simulations built around the two-circuit format of the
              Royal College of Psychiatrists&apos; exam.
            </p>
          </div>
          <dl className="mt-12 grid grid-cols-1 gap-6 sm:mt-16 sm:grid-cols-3">
            {examFormat.map((fact) => (
              <div key={fact.label} className={`${type.featureCard} text-center`}>
                <dt className="sr-only">{fact.label}</dt>
                <dd>
                  <span className={`block ${type.sectionTitle}`}>{fact.value}</span>
                  <span className={`mt-2 block ${type.itemBody}`}>{fact.label}</span>
                </dd>
              </div>
            ))}
          </dl>
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
              Marking grounded in UK practice (NICE, the Mental Health Act and
              the Mental Capacity Act) and analytics that show where to focus.
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
          <div className="mt-12 sm:mt-16">
            <LandingProgressShowcase variant="casc" className="mx-auto max-w-5xl" />
          </div>
        </div>
      </section>

      <PracticeWithColleaguesSection />
      <NeurodiversitySupportSection />
      <LandingPricingSection appType="casc" />
      <FAQSection />
      <ExamBlogRail examCode="casc" />
      <LandingFooter sectionLinkPrefix="/" />
    </>
  );
}

export default function CascLandingPage() {
  return (
    <ExamLandingShell appType="casc">
      <CascLandingContent />
    </ExamLandingShell>
  );
}
