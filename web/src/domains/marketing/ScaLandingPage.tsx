"use client";

import { usePartnerContext } from "@/domains/marketing/support/usePartnerContext";

import { LuBot, LuTimer } from "react-icons/lu";
import { HiOutlineChatBubbleLeftRight, HiOutlineClipboardDocumentCheck, HiOutlineHeart, HiOutlineNumberedList, HiOutlinePresentationChartLine } from "react-icons/hi2";
import { useMemo } from "react";
import { CAPABILITIES } from "@/domains/marketing/support/constants";
import { FAQSection } from "./FAQ";
import { LandingDemoVideo } from "./LandingDemoVideo";
import { PracticeWithColleaguesSection } from "./PracticeWithColleagues";
import { NeurodiversitySupportSection } from "./NeurodiversitySupportSection";
import { LandingPricingSection } from "./Pricing";
import Testimonials from "./Testimonials";
import { LandingFooter } from "./LandingFooter";
import { ExamLandingShell } from "./ExamLandingShell";
import { ExamLandingHero } from "./ExamLandingHero";
import { ExamQuoteSection } from "./ExamQuoteSection";
import { LandingIconBadge } from "./LandingIconBadge";
import { LandingBlogSection } from "./sections/LandingBlogSection";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";
import type { LandingIconColor } from "./landingIconPalette";
import { LandingFeedbackShowcase } from "./showcases/LandingFeedbackShowcase";
import { LandingProgressShowcase } from "./showcases/LandingProgressShowcase";
import { LandingSimulationShowcase } from "./showcases/LandingSimulationShowcase";
import { LOGIN_PATH, REGISTER_PATH } from "@/domains/marketing/support/partnerConstants";

const scaDomains = CAPABILITIES.slice(0, 6).map((item) => item.capability);

const workflow: Array<{
  icon: typeof LuBot;
  color: LandingIconColor;
  title: string;
  description: string;
}> = [
  {
    icon: LuBot,
    color: "cyan",
    title: "Available 24/7",
    description:
      "Practice anytime, anywhere with AI patients that respond like real humans.",
  },
  {
    icon: LuTimer,
    color: "teal",
    title: "Own the 12-minute clock",
    description:
      "Create as many timed mocks as you like to perfect your time management.",
  },
  {
    icon: HiOutlineChatBubbleLeftRight,
    color: "indigo",
    title: "Decode examiner insights",
    description: "Instant feedback based on the SCA exam grading domains.",
  },
  {
    icon: HiOutlinePresentationChartLine,
    color: "blue",
    title: "Track measurable gains",
    description:
      "Monitor your progress, know exactly where you need to improve and get feedback on your weak areas.",
  },
];

const SCA_DEMO_VIDEO_SRC =
  "https://osceguide.s3.eu-west-2.amazonaws.com/Four+Integers+Ltd/osceguide-sca.mp4";

function ScaLandingContent() {
  const partner = usePartnerContext();
  const { type } = useLandingVariant();

  const domainColumns = useMemo(() => {
    const midpoint = Math.ceil(scaDomains.length / 2);
    return [scaDomains.slice(0, midpoint), scaDomains.slice(midpoint)];
  }, []);

  return (
    <>
      <ExamLandingHero
        appType="sca"
        testimonialsHref="#testimonials"
        title={
          <>
            <span className="block">
              Master the <span className="text-osce-accent">SCA exam</span>
            </span>
            <span className="block">with voice-first AI practice</span>
          </>
        }
        lead="Practice your time management, stress-test your data gathering and lock in examiner-grade feedback before exam day."
      />

      <section
        id="demo"
        className={`scroll-mt-20 ${landingSectionSurfaces.plain} ${type.sectionPaddingCompact}`}
      >
        <div className={`${type.sectionShell} text-center`}>
          <h2 className={type.sectionTitle}>See OSCE Guide in Action</h2>
          <LandingDemoVideo
            src={SCA_DEMO_VIDEO_SRC}
            title="OSCE Guide SCA demo"
            className="mx-auto mt-10 max-w-5xl sm:mt-12"
          />
        </div>
      </section>

      <section
        className={`scroll-mt-20 ${landingSectionSurfaces.features} ${type.sectionPaddingCompact}`}
      >
        <div className={`${type.sectionShell} flex flex-col gap-10`}>
          <div className="text-center">
            <h2 className={type.sectionTitle}>
              Your guided workflow for the SCA exam
            </h2>
            <p className={type.sectionSubtitleCentered}>
              Use deliberate practice cycles to build fluency across data
              gathering, clinical management, and interpersonal skills.
            </p>
          </div>
          <div className="grid gap-6 sm:gap-8 md:grid-cols-2">
            {workflow.map((item) => (
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
            <h2 className={type.sectionTitle}>
              Cover every Clinical Experience Group with confidence
            </h2>
            <p className={`${type.sectionSubtitle} lg:mx-0`}>
              Build breadth without losing depth. Our stations are carefully
              curated by practicing GPs across all clinical experience groups so
              no theme feels unfamiliar on exam day.
            </p>
          </div>
          <div className="grid flex-1 gap-6 sm:gap-8 md:grid-cols-2">
            {domainColumns.map((column, index) => (
              <ul
                key={index}
                className="space-y-3 rounded-landing-card border border-landing-warm bg-landing-card p-5 shadow-landing-card sm:space-y-4 sm:p-6"
              >
                {column.map((domain) => (
                  <li key={domain} className={type.listItem}>
                    <span className="mt-1 inline-flex h-2 w-2 flex-shrink-0 rounded-full bg-osce-accent sm:h-2.5 sm:w-2.5" />
                    {domain}
                  </li>
                ))}
              </ul>
            ))}
          </div>
        </div>
      </section>

      <section
        id="feedback"
        className={`scroll-mt-20 ${landingSectionSurfaces.practice} ${type.sectionPadding}`}
      >
        <div className={type.sectionShell}>
          <div className="mb-12 text-center sm:mb-16">
            <h2 className={type.sectionTitle}>
              Detailed Feedback &amp; Assessment
            </h2>
          </div>
          <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
            <div className="space-y-6 sm:space-y-8">
              {[
                {
                  icon: HiOutlineChatBubbleLeftRight,
                  color: "indigo" as const,
                  title: "Global Skills Analysis",
                  description:
                    "Receive feedback on communication, data gathering, and clinical management skills",
                },
                {
                  icon: HiOutlineClipboardDocumentCheck,
                  color: "blue" as const,
                  title: "Task-Specific Feedback",
                  description:
                    "Get detailed assessment on how well you complete required tasks",
                },
                {
                  icon: HiOutlinePresentationChartLine,
                  color: "green" as const,
                  title: "Professional Development",
                  description:
                    "Track your progress and identify areas for improvement",
                },
              ].map((item) => (
                <div key={item.title} className="flex gap-4">
                  <LandingIconBadge
                    icon={item.icon}
                    color={item.color}
                    size="sm"
                  />
                  <div>
                    <h3 className={type.itemTitle}>{item.title}</h3>
                    <p className={type.itemBody}>{item.description}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="relative">
              <LandingFeedbackShowcase variant="sca" />
            </div>
          </div>
        </div>
      </section>

      <section
        id="management"
        className={`scroll-mt-20 ${landingSectionSurfaces.plain} ${type.sectionPadding}`}
      >
        <div className={type.sectionShell}>
          <div className="mb-12 text-center sm:mb-16">
            <h2 className={type.sectionTitle}>Clinical Management</h2>
          </div>
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3 sm:gap-10">
            {[
              {
                icon: HiOutlineNumberedList,
                color: "blue" as const,
                title: "Structured Approach",
                description:
                  "Follow a systematic approach to clinical management ",
              },
              {
                icon: HiOutlineClipboardDocumentCheck,
                color: "indigo" as const,
                title: "Evidence-Based Management",
                description: "Access evidence-based management plans",
              },
              {
                icon: HiOutlineHeart,
                color: "violet" as const,
                title: "Holistic Care Planning",
                description:
                  "Address both clinical and psychosocial aspects of patient care",
              },
            ].map((item) => (
              <div key={item.title}>
                <LandingIconBadge icon={item.icon} color={item.color} size="sm" />
                <h3 className={`mt-4 ${type.itemTitle}`}>{item.title}</h3>
                <p className={`mt-2 ${type.itemBody}`}>{item.description}</p>
              </div>
            ))}
          </div>
          <div className="mt-12 sm:mt-16">
            <LandingSimulationShowcase variant="sca" />
          </div>
        </div>
      </section>

      <section
        id="progress"
        className={`scroll-mt-20 ${landingSectionSurfaces.features} ${type.sectionPaddingCompact}`}
      >
        <div className={type.sectionShell}>
          <div className="mb-10 text-center sm:mb-12">
            <h2 className={type.sectionTitle}>Know exactly where you stand</h2>
            <p className={type.sectionSubtitleCentered}>
              Every marked station feeds one dashboard, so you can see which
              domain is holding you back long before exam day.
            </p>
          </div>
          <LandingProgressShowcase variant="sca" className="mx-auto max-w-5xl" />
        </div>
      </section>

      <PracticeWithColleaguesSection />
      <NeurodiversitySupportSection />

      <ExamQuoteSection
        quote={`"I loved being able to practise at my own pace without waiting for colleagues who were busy. The cases were varied, and the focused feedback helped me most. I've just passed my SCA with a score of 98 and 18 clear passes, so OSCE Guide clearly made a difference!"`}
        attribution="Dr Faith Olokada · Passed November 2025 SCA"
      />

      <Testimonials
        titleBefore="Doctors who "
        titleHighlight="passed"
        titleAfter=" recommend OSCE Guide"
        description={null}
        primaryCta={{
          label: "Register",
          href: partner.href(REGISTER_PATH, "sca"),
        }}
        secondaryCta={{ label: "Log in", href: partner.href(LOGIN_PATH, "sca") }}
      />

      <LandingPricingSection appType="sca" />
      <FAQSection />

      <LandingBlogSection />

      <LandingFooter sectionLinkPrefix="/" />
    </>
  );
}

const ScaLandingPage = () => (
  <ExamLandingShell appType="sca">
    <ScaLandingContent />
  </ExamLandingShell>
);

export default ScaLandingPage;
