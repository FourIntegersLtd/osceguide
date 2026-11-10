import {
  HiOutlineChatBubbleLeftRight,
  HiOutlineClipboardDocumentList,
  HiOutlineScale,
  HiOutlineShieldCheck,
} from "react-icons/hi2";
import { ExamBlogRail } from "@/capabilities/media";
import { CardGrid, TitledSection } from "@/domains/marketing/home/Blocks";
import { ExamFacts } from "@/domains/marketing/exam/ExamBlocks";
import { ExamHero } from "@/domains/marketing/exam/ExamHero";
import { HomeFaq } from "@/domains/marketing/home/HomeFaq";
import { HomeNeurodiversity, HomePractice } from "@/domains/marketing/home/HomePractice";
import { HomeFounders } from "@/domains/marketing/home/HomeVoices";
import { LandingPricingSection } from "@/domains/marketing/Pricing";
import { LandingProgressShowcase } from "@/domains/marketing/showcases/LandingProgressShowcase";
import { LandingSimulationShowcase } from "@/domains/marketing/showcases/LandingSimulationShowcase";
import { SiteShell } from "@/domains/marketing/site/SiteShell";

/** The three skills a CASC examiner is looking for in almost every station. */
const cascHighlights = [
  {
    Icon: HiOutlineShieldCheck,
    title: "Risk, asked out loud",
    body: "Rehearse the direct, sensitive questions about suicide, self-harm, harm to others and self-neglect until they come naturally.",
  },
  {
    Icon: HiOutlineScale,
    title: "Mental state and capacity",
    body: "Work through a systematic mental state examination and a Mental Capacity Act assessment against the clock.",
  },
  {
    Icon: HiOutlineChatBubbleLeftRight,
    title: "Explaining and negotiating",
    body: "Explain diagnoses and treatments to patients, relatives and colleagues in plain, non-stigmatising language.",
  },
];

/** The CASC's three station families, as the college groups them. */
const stationTypes = [
  {
    title: "History taking & risk",
    body: "Focused psychiatric histories across general adult, old age, CAMHS, perinatal, substance misuse and forensic presentations, with the risk assessment built in.",
  },
  {
    title: "Examination",
    body: "Mental state, cognitive and targeted physical examinations, plus capacity assessments, each marked on what the task asked of you.",
  },
  {
    title: "Management & communication",
    body: "Discuss a plan with a worried relative, explain medication such as lithium or clozapine, or hand over to a colleague, using the Mental Health Act where it applies.",
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
    Icon: HiOutlineClipboardDocumentList,
    title: "Discover",
    body: "Practise CASC-style stations written by psychiatrists, with role players who respond to your tone as well as your questions.",
  },
  {
    Icon: HiOutlineClipboardDocumentList,
    title: "Diagnose",
    body: "See every station marked across history, examination, management and communication, with quotes from your own transcript.",
  },
  {
    Icon: HiOutlineClipboardDocumentList,
    title: "Deliver",
    body: "Debrief with Athena, our AI tutor, on the risk questions you missed and the explanation you could make clearer, then run the station again.",
  },
];

export default function CascLandingPage() {
  return (
    <SiteShell exam="casc">
      <ExamHero
        exam="casc"
        title={
          <>
            <span className="block">Pass the MRCPsych CASC with</span>
            <span className="block text-site-brand">voice-first AI practice</span>
          </>
        }
        lead="Rehearse risk assessments, mental state examinations and difficult conversations with an AI role player, marked as you speak, so you walk into all 16 stations calm and fluent."
      />

      <HomeFounders />

      <TitledSection
        tone="card"
        title="Seven minutes, one task, out loud"
        sub="CASC stations reward the doctor who completes the task safely and empathically. Practise saying it, not just knowing it."
      >
        <CardGrid items={cascHighlights} />
        <LandingSimulationShowcase variant="casc" />
      </TitledSection>

      <TitledSection
        title="Nail every CASC station type"
        sub="Voice simulations built around the two-circuit format of the Royal College of Psychiatrists' exam."
      >
        <ExamFacts facts={examFormat} />
        <CardGrid items={stationTypes} />
      </TitledSection>

      <TitledSection
        tone="card"
        title="The fastest loop from practice to pass"
        sub="Marking grounded in UK practice (NICE, the Mental Health Act and the Mental Capacity Act) and analytics that show where to focus."
      >
        <CardGrid items={preparationWorkflow} />
        <LandingProgressShowcase variant="casc" className="mx-auto max-w-5xl" />
      </TitledSection>

      <HomePractice
        eyebrow=""
        title="Practice with Colleagues"
      />
      <HomeNeurodiversity />
      <LandingPricingSection appType="casc" />
      <HomeFaq />
      <ExamBlogRail examCode="casc" />
    </SiteShell>
  );
}
