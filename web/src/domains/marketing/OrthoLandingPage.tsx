"use client";

import { LuHeartHandshake, LuMicroscope } from "react-icons/lu";
import { HiOutlineClipboardDocumentList } from "react-icons/hi2";
import { useMemo } from "react";
import { MdOutlineQuestionAnswer } from "react-icons/md";
import { FAQSection } from "./FAQ";
import { ExamBlogRail } from "@/capabilities/media";
import { LandingFooter } from "./LandingFooter";
import { LandingPricingSection } from "./Pricing";
import { ExamLandingShell } from "./ExamLandingShell";
import { ExamLandingHero } from "./ExamLandingHero";
import { ExamQuoteSection } from "./ExamQuoteSection";
import { LandingIconBadge } from "./LandingIconBadge";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";
import type { LandingIconColor } from "./landingIconPalette";
import {
  LandingPrioritisationShowcase,
  LandingSimulationShowcase,
} from "./showcases/LandingSimulationShowcase";

const interviewStations: Array<{
  icon: typeof LuMicroscope;
  color: LandingIconColor;
  title: string;
  description: string;
}> = [
  {
    icon: LuMicroscope,
    color: "blue",
    title: "Clinical Stations",
    description:
      "Two consultant interviewers present trauma or elective scenarios and ask structured questions on assessment, anatomy, BOAST guidelines, and operative planning, just like the national ST3 clinical station.",
  },
  {
    icon: HiOutlineClipboardDocumentList,
    color: "orange",
    title: "Prioritisation Station",
    description:
      "Work through a trauma list handover with interviewers asking how you would rank cases, organise theatre, and communicate your plan under time pressure.",
  },
  {
    icon: MdOutlineQuestionAnswer,
    color: "indigo",
    title: "Commitment to Specialty",
    description:
      "Interviewers question you on career motivation, leadership, organisation, and academic work, matching the portfolio station in UK ST3 selection.",
  },
  {
    icon: LuHeartHandshake,
    color: "violet",
    title: "Communication Station",
    description:
      "The one patient-facing station: practise consent, breaking bad news, and capacity with an AI patient actor, marked on communication and judgement under pressure.",
  },
];

const anatomicalAreas = [
  "Shoulder & Elbow",
  "Hand & Wrist",
  "Hip & Pelvis",
  "Knee & Lower Leg",
  "Foot & Ankle",
  "Paediatrics",
  "Spine",
  "Orthopaedic Principles",
];

function OrthoLandingContent() {
  const { type } = useLandingVariant();

  const areaColumns = useMemo(() => {
    const midpoint = Math.ceil(anatomicalAreas.length / 2);
    return [
      anatomicalAreas.slice(0, midpoint),
      anatomicalAreas.slice(midpoint),
    ];
  }, []);

  return (
    <>
      <ExamLandingHero
        appType="ortho"
        title={
          <>
            <span className="block">
              Master the{" "}
              <span className="text-osce-accent">orthopaedic ST3 interview</span>
            </span>
            <span className="block">with voice-first AI practice</span>
          </>
        }
        lead="Rehearse every interview station with AI voice simulations that stress-test your clinical reasoning, prioritisation, portfolio, and communication before interview day."
      />

      <section
        className={`scroll-mt-20 ${landingSectionSurfaces.plain} ${type.sectionPaddingCompact}`}
      >
        <div className={`${type.sectionShell} space-y-10`}>
          <div className="text-center">
            <h2 className={type.sectionTitle}>See OSCE Guide in Action</h2>
            <p className={type.sectionSubtitleCentered}>
              Rehearse consultant-led clinical questioning with live voice
              transcripts and structured marking as you answer.
            </p>
          </div>
          <LandingSimulationShowcase variant="ortho" />
        </div>
      </section>

      <section
        className={`scroll-mt-20 ${landingSectionSurfaces.features} ${type.sectionPaddingCompact}`}
      >
        <div className={`${type.sectionShell} flex flex-col gap-10`}>
          <div className="text-center">
            <h2 className={type.sectionTitle}>
              Four-Station Interview Preparation
            </h2>
            <p className={type.sectionSubtitleCentered}>
              Master each station with our systematic approach and reproducible
              frameworks.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-6 sm:gap-8 md:grid-cols-2">
            {interviewStations.map((item) => (
              <div key={item.title} className={type.featureCardMuted}>
                <LandingIconBadge icon={item.icon} color={item.color} size="md" />
                <h3 className={`mt-5 ${type.itemTitle}`}>{item.title}</h3>
                <p className={`mt-3 ${type.itemBody}`}>{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section
        className={`scroll-mt-20 ${landingSectionSurfaces.exams} ${type.sectionPaddingCompact}`}
      >
        <div
          className={`${type.sectionShell} flex flex-col gap-10 lg:flex-row lg:gap-12`}
        >
          <div className="flex-1 text-center lg:text-left">
            <h2 className={type.sectionTitle}>Anatomic Area-Based Learning</h2>
            <p className={`${type.sectionSubtitle} lg:mx-0`}>
              Tackle each anatomical area comprehensively, covering relevant
              anatomy, clinical stations, surgical approaches, and operations to
              consolidate your knowledge.
            </p>
          </div>
          <div className="grid grid-cols-1 flex-1 gap-6 sm:gap-8 md:grid-cols-2">
            {areaColumns.map((column, index) => (
              <ul
                key={index}
                className="space-y-3 rounded-landing-card border border-landing-warm bg-landing-card p-5 shadow-landing-card sm:space-y-4 sm:p-6"
              >
                {column.map((area) => (
                  <li key={area} className={type.listItem}>
                    <span className="mt-1 inline-flex h-2 w-2 flex-shrink-0 rounded-full bg-osce-accent sm:h-2.5 sm:w-2.5" />
                    {area}
                  </li>
                ))}
              </ul>
            ))}
          </div>
        </div>
      </section>

      <section
        className={`scroll-mt-20 ${landingSectionSurfaces.plain} ${type.sectionPaddingCompact}`}
      >
        <div className={type.sectionShell}>
          <div className="flex flex-col gap-10 lg:flex-row lg:items-center lg:gap-12">
            <div className="lg:w-[42%] lg:flex-shrink-0">
              <h2 className={type.sectionTitle}>Prioritisation Station</h2>
              <p className={type.sectionSubtitle}>
                Learn a structured approach to ranking trauma lists under pressure,
                with multiple scenarios that mirror what you face on interview day.
              </p>
            </div>
            <div className="min-w-0 flex-1">
              <LandingPrioritisationShowcase />
            </div>
          </div>
        </div>
      </section>

      <ExamQuoteSection
        quote={`"OSCE Guide helped me secure an ST3 position. The voice practice sessions built my confidence articulating surgical approaches and BOAST guidelines under pressure. The prioritisation scenarios mirrored what I faced on the day."`}
        attribution="Mark, ST3 Orthopaedic Registrar"
      />

      <FAQSection />
      <LandingPricingSection appType="ortho" />
      <ExamBlogRail examCode="ortho" />
      <LandingFooter sectionLinkPrefix="/" />
    </>
  );
}

const OrthoLandingPage = () => (
  <ExamLandingShell appType="ortho">
    <OrthoLandingContent />
  </ExamLandingShell>
);

export default OrthoLandingPage;
