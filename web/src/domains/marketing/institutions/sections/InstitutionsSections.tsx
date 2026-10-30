import { FiArrowRight } from "react-icons/fi";
import { LOGIN_PATH } from "@/foundation/attribution/partnerConstants";
import { Eyebrow, IconTile, SectionHead, SiteButtonLink } from "@/foundation/ui";
import { BulletList, CARD_TITLE, CardGrid, HeroIntro, LetterCard, SITE_CARD } from "@/domains/marketing/home/Blocks";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { Section } from "@/domains/marketing/home/Section";
import { B2bMarketingScreenshot } from "../components/B2bMarketingScreenshot";
import { InstitutionsHeroCircuitShowcase } from "../components/InstitutionsHeroCircuitShowcase";
import {
  BUYER_TYPES,
  DEMO_MAILTO,
  EXAM_BULLETS,
  HOW_IT_WORKS_STEPS,
  PLATFORM_FEATURES,
  TRAINING_BULLETS,
  VALUE_PROPS,
} from "../institutionsLandingContent";

const VALUE_CARDS = VALUE_PROPS.map(({ icon, label, body }) => ({ Icon: icon, title: label, body }));
const STEP_CARDS = HOW_IT_WORKS_STEPS.map(({ icon, step, title, body }) => ({ Icon: icon, label: step, title, body }));

export function InstitutionsHeroSection() {
  return (
    <section className="px-4 pb-16 pt-10 text-center sm:px-6 sm:pt-16">
      <div className="mx-auto max-w-[1200px]">
        <HeroIntro
          title={
            <>
              <span className="block">Run training &amp; exam days</span>
              <span className="block">with virtual patients</span>
            </>
          }
          lead="OSCE Guide helps institutions run OSCE training sessions and full exam days with virtual patients. Candidates get more time to practise, faculty spend less time on setup, and sessions stay on schedule."
          ctas={
            <>
              <SiteButtonLink href={DEMO_MAILTO} size="lg">
                Book a demo <FiArrowRight aria-hidden />
              </SiteButtonLink>
              <PartnerLink path={LOGIN_PATH} variant="line" size="lg">
                Log in
              </PartnerLink>
            </>
          }
        />
        <div className="mx-auto mt-12 max-w-[1000px]">
          <InstitutionsHeroCircuitShowcase />
        </div>
      </div>
    </section>
  );
}

export function InstitutionsValueSection() {
  return (
    <Section tone="card">
      <SectionHead eyebrow="What OSCE Guide does" title="Your complete OSCE platform for institutions" sub="Practice, feedback, and exam-day workflows in one platform." />
      <div className="mt-12">
        <CardGrid items={VALUE_CARDS} />
      </div>
    </Section>
  );
}

export function InstitutionsBuyerSection() {
  return (
    <Section id="for">
      <SectionHead
        eyebrow="Who it's for"
        title="Built for programmes that run OSCEs"
        sub="Undergraduate, postgraduate, and workforce programmes on one platform. You bring stations and marking schemes. We handle the rest."
      />
      <div className="mt-12 grid gap-5 lg:grid-cols-2">
        {BUYER_TYPES.map((buyer) => (
          <article key={buyer.label} className={`${SITE_CARD} sm:p-8`}>
            <h3 className={CARD_TITLE}>{buyer.label}</h3>
            <p className="mt-2 leading-relaxed text-site-body">{buyer.description}</p>
            <div className="mt-5">
              <BulletList items={buyer.examples} />
            </div>
          </article>
        ))}
      </div>
    </Section>
  );
}

export function InstitutionsHowSection() {
  return (
    <Section id="how" tone="pale">
      <SectionHead
        eyebrow="How it works"
        title="From candidate consultation to faculty oversight"
        sub="Each station follows a fixed sequence: the candidate consults a virtual patient by voice, supervisors observe in real time, and feedback is recorded against your marking criteria."
      />
      <div className="mt-12">
        <CardGrid items={STEP_CARDS} className="sm:grid-cols-2 lg:grid-cols-4" />
      </div>
    </Section>
  );
}

export function InstitutionsPlatformSection() {
  return (
    <Section id="platform" tone="card">
      <div className="grid gap-12 lg:grid-cols-12 lg:items-center">
        <div className="lg:col-span-5">
          <Eyebrow>Platform</Eyebrow>
          <h2 className="mt-3 text-balance font-landing-heading text-3xl font-bold leading-tight text-site-ink">Everything in one place for your programme</h2>
          <ul className="mt-8 space-y-4">
            {PLATFORM_FEATURES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-site-body">
                <IconTile><Icon /></IconTile>
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="lg:col-span-7">
          <B2bMarketingScreenshot
            alt="Organisation dashboard with setup progress, sessions, and trainee roster"
            caption="See what is ready before you open the circuit, and what still needs attention."
            maxHeightClass="max-h-[min(480px,62vh)]"
          />
        </div>
      </div>
    </Section>
  );
}

function ModeCard({ eyebrow, title, body, bullets, footer }: { eyebrow: string; title: string; body: string; bullets: readonly string[]; footer?: string }) {
  return (
    <article className={`flex flex-col gap-6 ${SITE_CARD} sm:p-8`}>
      <div>
        <Eyebrow>{eyebrow}</Eyebrow>
        <h3 className={`${CARD_TITLE} mt-3`}>{title}</h3>
        <p className="mt-2 leading-relaxed text-site-body">{body}</p>
      </div>
      <BulletList items={bullets} />
      {footer && <p className="border-t border-site-line pt-4 leading-relaxed text-site-body">{footer}</p>}
    </article>
  );
}

export function InstitutionsModesSection() {
  return (
    <Section>
      <SectionHead eyebrow="Session types" title="Training sessions and exam circuits" sub="One platform for formative practice and formal assessment. Each mode follows your programme's rules." />
      <div className="mt-12 grid gap-5 lg:grid-cols-2">
        <ModeCard
          eyebrow="Training sessions"
          title="Formative practice for your cohort"
          body="For skills weeks and prep sessions. Supervisors set the pace, take notes, and give feedback in exam-day format."
          bullets={TRAINING_BULLETS}
        />
        <ModeCard
          eyebrow="Exam circuits"
          title="Formal assessment on exam day"
          body="For assessment days. Supervisors observe only; feedback waits for examiner approval. Every station is logged."
          bullets={EXAM_BULLETS}
          footer="Summative use is a governance decision for your programme. We'll explain what the platform handles and where examiner oversight stays with faculty."
        />
      </div>
    </Section>
  );
}

const ABOUT_PARAGRAPHS = [
  "OSCE Guide was created by practising doctors who spent years on both sides of the assessment room. We designed the platform for real exam days, when timetables shift, rooms change, and faculty need tools that keep the circuit moving.",
  "We built what we wished we had when running circuits ourselves: clear oversight for supervisors, consistent virtual patients for every candidate, and feedback that maps to your marking criteria.",
] as const;

export function InstitutionsAboutSection() {
  return (
    <Section tone="pale">
      <LetterCard
        eyebrow="About us"
        title="Built by clinicians who have run these exams"
        paragraphs={ABOUT_PARAGRAPHS}
        signoff={
          <>
            <b className="text-site-ink">OSCE Guide</b>
            <span>Built by clinicians, for exam day</span>
          </>
        }
      />
    </Section>
  );
}

export function InstitutionsCtaSection() {
  return (
    <Section id="contact" tone="navy">
      <SectionHead
        onNavy
        title="See OSCE Guide for your programme"
        sub="Book a demo to walk through training sessions, exam circuits, and how we support your faculty on the day."
      />
      <div className="mt-8 flex justify-center">
        <SiteButtonLink href={DEMO_MAILTO} variant="white" size="lg">
          Book a demo
        </SiteButtonLink>
      </div>
    </Section>
  );
}
