import { LuBot, LuTimer } from "react-icons/lu";
import {
  HiOutlineChatBubbleLeftRight,
  HiOutlineClipboardDocumentCheck,
  HiOutlineHeart,
  HiOutlineNumberedList,
  HiOutlinePresentationChartLine,
} from "react-icons/hi2";
import { LOGIN_PATH, REGISTER_PATH } from "@/foundation/attribution/partnerConstants";
import { CAPABILITIES } from "@/domains/marketing/support/constants";
import { CardGrid, Checklist, TitledSection } from "@/domains/marketing/home/Blocks";
import { ExamQuote } from "@/domains/marketing/exam/ExamBlocks";
import { ExamHero } from "@/domains/marketing/exam/ExamHero";
import { HomeFaq } from "@/domains/marketing/home/HomeFaq";
import { HomeNeurodiversity, HomePractice } from "@/domains/marketing/home/HomePractice";
import { HomeTestimonials } from "@/domains/marketing/home/HomeVoices";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { LandingDemoVideo } from "@/domains/marketing/LandingDemoVideo";
import { LandingPricingSection } from "@/domains/marketing/Pricing";
import { LandingBlogSection } from "@/domains/marketing/sections/LandingBlogSection";
import { LandingFeedbackShowcase } from "@/domains/marketing/showcases/LandingFeedbackShowcase";
import { LandingProgressShowcase } from "@/domains/marketing/showcases/LandingProgressShowcase";
import { LandingSimulationShowcase } from "@/domains/marketing/showcases/LandingSimulationShowcase";
import { SiteShell } from "@/domains/marketing/site/SiteShell";

const scaDomains = CAPABILITIES.slice(0, 6).map((item) => item.capability);
const midpoint = Math.ceil(scaDomains.length / 2);
const domainColumns = [scaDomains.slice(0, midpoint), scaDomains.slice(midpoint)];

const workflow = [
  { Icon: LuBot, title: "Available 24/7", body: "Practice anytime, anywhere with AI patients that respond like real humans." },
  { Icon: LuTimer, title: "Own the 12-minute clock", body: "Create as many timed mocks as you like to perfect your time management." },
  { Icon: HiOutlineChatBubbleLeftRight, title: "Decode examiner insights", body: "Instant feedback based on the SCA exam grading domains." },
  { Icon: HiOutlinePresentationChartLine, title: "Track measurable gains", body: "Monitor your progress, know exactly where you need to improve and get feedback on your weak areas." },
];

const feedback = [
  { Icon: HiOutlineChatBubbleLeftRight, title: "Global Skills Analysis", body: "Receive feedback on communication, data gathering, and clinical management skills" },
  { Icon: HiOutlineClipboardDocumentCheck, title: "Task-Specific Feedback", body: "Get detailed assessment on how well you complete required tasks" },
  { Icon: HiOutlinePresentationChartLine, title: "Professional Development", body: "Track your progress and identify areas for improvement" },
];

const management = [
  { Icon: HiOutlineNumberedList, title: "Structured Approach", body: "Follow a systematic approach to clinical management " },
  { Icon: HiOutlineClipboardDocumentCheck, title: "Evidence-Based Management", body: "Access evidence-based management plans" },
  { Icon: HiOutlineHeart, title: "Holistic Care Planning", body: "Address both clinical and psychosocial aspects of patient care" },
];

const SCA_DEMO_VIDEO_SRC = "https://d1wmb89lczbkpf.cloudfront.net/marketing/osceguide-sca.mp4";

const ScaLandingPage = () => (
  <SiteShell exam="sca">
    <ExamHero
      exam="sca"
      testimonialsHref="#testimonials"
      title={
        <>
          <span className="block">
            Master the <span className="text-site-brand">SCA exam</span>
          </span>
          <span className="block">with voice-first AI practice</span>
        </>
      }
      lead="Practice your time management, stress-test your data gathering and lock in examiner-grade feedback before exam day."
    />

    <TitledSection id="demo" tone="card" title="See OSCE Guide in Action">
      <LandingDemoVideo src={SCA_DEMO_VIDEO_SRC} title="OSCE Guide SCA demo" className="mx-auto max-w-5xl" />
    </TitledSection>

    <TitledSection
      title="Your guided workflow for the SCA exam"
      sub="Use deliberate practice cycles to build fluency across data gathering, clinical management, and interpersonal skills."
    >
      <CardGrid items={workflow} className="md:grid-cols-2" />
    </TitledSection>

    <TitledSection
      tone="card"
      title="Cover every Clinical Experience Group with confidence"
      sub="Build breadth without losing depth. Our stations are carefully curated by practicing GPs across all clinical experience groups so no theme feels unfamiliar on exam day."
    >
      <Checklist columns={domainColumns} />
    </TitledSection>

    <TitledSection id="feedback" title="Detailed Feedback & Assessment">
      <div className="grid items-center gap-12 lg:grid-cols-2">
        <CardGrid items={feedback} className="grid-cols-1" />
        <LandingFeedbackShowcase variant="sca" />
      </div>
    </TitledSection>

    <TitledSection id="management" tone="card" title="Clinical Management">
      <CardGrid items={management} />
      <LandingSimulationShowcase variant="sca" />
    </TitledSection>

    <TitledSection
      id="progress"
      title="Know exactly where you stand"
      sub="Every marked station feeds one dashboard, so you can see which domain is holding you back long before exam day."
    >
      <LandingProgressShowcase variant="sca" className="mx-auto max-w-5xl" />
    </TitledSection>

    <HomePractice
      eyebrow=""
      title="Practice with Colleagues"
    />
    <HomeNeurodiversity />

    <ExamQuote
      quote={`"I loved being able to practise at my own pace without waiting for colleagues who were busy. The cases were varied, and the focused feedback helped me most. I've just passed my SCA with a score of 98 and 18 clear passes, so OSCE Guide clearly made a difference!"`}
      attribution="Dr Faith Olokada · Passed November 2025 SCA"
    />

    <HomeTestimonials
      title={
        <>
          Doctors who <span className="text-site-brand">passed</span> recommend OSCE Guide
        </>
      }
      ctas={
        <>
          <PartnerLink path={REGISTER_PATH} exam="sca" size="lg">Register</PartnerLink>
          <PartnerLink path={LOGIN_PATH} exam="sca" variant="line" size="lg">Log in</PartnerLink>
        </>
      }
    />

    <LandingPricingSection appType="sca" />
    <HomeFaq openFirst />
    <LandingBlogSection />
  </SiteShell>
);

export default ScaLandingPage;
