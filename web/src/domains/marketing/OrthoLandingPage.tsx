import { LuHeartHandshake, LuMicroscope } from "react-icons/lu";
import { HiOutlineClipboardDocumentList } from "react-icons/hi2";
import { MdOutlineQuestionAnswer } from "react-icons/md";
import { ExamBlogRail } from "@/capabilities/media";
import { CardGrid, Checklist, TitledSection } from "@/domains/marketing/home/Blocks";
import { ExamQuote } from "@/domains/marketing/exam/ExamBlocks";
import { ExamHero } from "@/domains/marketing/exam/ExamHero";
import { HomeFaq } from "@/domains/marketing/home/HomeFaq";
import { LandingPricingSection } from "@/domains/marketing/Pricing";
import { LandingPrioritisationShowcase, LandingSimulationShowcase } from "@/domains/marketing/showcases/LandingSimulationShowcase";
import { SiteShell } from "@/domains/marketing/site/SiteShell";

const interviewStations = [
  {
    Icon: LuMicroscope,
    title: "Clinical Stations",
    body: "Two consultant interviewers present trauma or elective scenarios and ask structured questions on assessment, anatomy, BOAST guidelines, and operative planning, just like the national ST3 clinical station.",
  },
  {
    Icon: HiOutlineClipboardDocumentList,
    title: "Prioritisation Station",
    body: "Work through a trauma list handover with interviewers asking how you would rank cases, organise theatre, and communicate your plan under time pressure.",
  },
  {
    Icon: MdOutlineQuestionAnswer,
    title: "Commitment to Specialty",
    body: "Interviewers question you on career motivation, leadership, organisation, and academic work, matching the portfolio station in UK ST3 selection.",
  },
  {
    Icon: LuHeartHandshake,
    title: "Communication Station",
    body: "The one patient-facing station: practise consent, breaking bad news, and capacity with an AI patient actor, marked on communication and judgement under pressure.",
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
const midpoint = Math.ceil(anatomicalAreas.length / 2);
const areaColumns = [anatomicalAreas.slice(0, midpoint), anatomicalAreas.slice(midpoint)];

export default function OrthoLandingPage() {
  return (
    <SiteShell exam="ortho">
      <ExamHero
        exam="ortho"
        title={
          <>
            <span className="block">
              Master the <span className="text-site-brand">orthopaedic ST3 interview</span>
            </span>
            <span className="block">with voice-first AI practice</span>
          </>
        }
        lead="Rehearse every interview station with AI voice simulations that stress-test your clinical reasoning, prioritisation, portfolio, and communication before interview day."
      />

      <TitledSection
        tone="card"
        title="See OSCE Guide in Action"
        sub="Rehearse consultant-led clinical questioning with live voice transcripts and structured marking as you answer."
      >
        <LandingSimulationShowcase variant="ortho" />
      </TitledSection>

      <TitledSection
        title="Four-Station Interview Preparation"
        sub="Master each station with our systematic approach and reproducible frameworks."
      >
        <CardGrid items={interviewStations} className="md:grid-cols-2" />
      </TitledSection>

      <TitledSection
        tone="card"
        title="Anatomic Area-Based Learning"
        sub="Tackle each anatomical area comprehensively, covering relevant anatomy, clinical stations, surgical approaches, and operations to consolidate your knowledge."
      >
        <Checklist columns={areaColumns} />
      </TitledSection>

      <TitledSection
        title="Prioritisation Station"
        sub="Learn a structured approach to ranking trauma lists under pressure, with multiple scenarios that mirror what you face on interview day."
      >
        <LandingPrioritisationShowcase />
      </TitledSection>

      <ExamQuote
        quote={`"OSCE Guide helped me secure an ST3 position. The voice practice sessions built my confidence articulating surgical approaches and BOAST guidelines under pressure. The prioritisation scenarios mirrored what I faced on the day."`}
        attribution="Mark, ST3 Orthopaedic Registrar"
      />

      <HomeFaq openFirst />
      <LandingPricingSection appType="ortho" />
      <ExamBlogRail examCode="ortho" />
    </SiteShell>
  );
}
