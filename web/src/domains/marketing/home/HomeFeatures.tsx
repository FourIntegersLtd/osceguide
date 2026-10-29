import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { FiBarChart2, FiClock, FiGlobe, FiHeart, FiMic, FiVideo } from "react-icons/fi";
import { GiBoneKnife } from "react-icons/gi";
import { FaUserDoctor } from "react-icons/fa6";
import { ATHENA_IMAGE_SRC } from "@/foundation/ui/AthenaIdentity";
import { WaveBars } from "@/domains/marketing/home/HomeHero";
import { HomeClock } from "@/domains/marketing/home/HomeClock";
import { Pill } from "@/domains/marketing/home/ReportShowcase";
import { Eyebrow, IconTile, SectionHead } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";

const BUBBLE = "rounded-2xl rounded-bl-sm bg-site-pale px-4 py-2.5 text-sm text-site-body";
const BUBBLE_ME = "self-end rounded-2xl rounded-br-sm bg-site-brand px-4 py-2.5 text-sm text-site-on-brand";

function Cell({ className = "", children }: { className?: string; children: ReactNode }) {
  return <article className={`flex flex-col rounded-2xl border p-6 ${className}`}>{children}</article>;
}

export function HomeFeatures() {
  return (
    <Section id="features">
      <SectionHead title="Your complete OSCE solution" sub="Built by clinicians, focusing on what matters most for your success" />
      <div className="mt-12 grid gap-4 md:grid-cols-6">
        <Cell className="border-transparent bg-site-navy md:col-span-4">
          <IconTile onNavy><FiMic /></IconTile>
          <span className="mt-4"><Eyebrow onNavy>Voice stations</Eyebrow></span>
          <h3 className="mt-2 font-landing-heading text-2xl font-bold text-white">AI-Powered Simulations</h3>
          <p className="mt-2 text-site-on-navy">Realistic patients with high-stakes scenarios powered by advanced Voice AI technology.</p>
          <div aria-hidden="true" className="mt-6 grid gap-5 sm:grid-cols-2 sm:items-center">
            <WaveBars heights={[30, 70, 45, 90, 55, 35, 80, 60, 25, 65, 40, 85, 50]} className="h-20" />
            <div className="flex flex-col gap-2">
              <span className={BUBBLE}>It&apos;s been there every morning for three weeks.</span>
              <span className={BUBBLE_ME}>Is there anything in particular you&apos;ve been worried about?</span>
              <span className={BUBBLE}>Honestly, my aunt had a brain tumour…</span>
            </div>
          </div>
        </Cell>
        <Cell className="border-site-line bg-site-card md:col-span-2">
          <IconTile><FiBarChart2 /></IconTile>
          <span className="mt-4"><Eyebrow>Domain feedback</Eyebrow></span>
          <h3 className="mt-2 font-landing-heading text-xl font-bold text-site-ink">Examiner-Style Feedback</h3>
          <p className="mt-2 text-site-body">Every station returns a domain breakdown, the marks you earned, and the exact moment in your transcript where each was decided.</p>
          <div aria-hidden="true" className="mt-5 flex flex-wrap gap-2">
            <Pill tone="ok">Data gathering</Pill>
            <Pill tone="dev">Management</Pill>
            <Pill tone="ok">Relating</Pill>
          </div>
        </Cell>
        <Cell className="border-transparent bg-site-pale md:col-span-2">
          <IconTile><FiVideo /></IconTile>
          <span className="mt-4"><Eyebrow>Marketplace</Eyebrow></span>
          <h3 className="mt-2 font-landing-heading text-xl font-bold text-site-ink">Practice with Colleagues</h3>
          <p className="mt-2 text-site-body">Match instantly with colleagues or schedule a session that fits. Real-time video practice.</p>
          <div aria-hidden="true" className="mt-5 space-y-2 text-sm text-site-ink">
            <span className="block rounded-lg bg-site-card px-3 py-2">Tue 19:00 <small className="text-site-muted">You play the doctor</small></span>
            <span className="block rounded-lg bg-site-card px-3 py-2">Wed 07:30 <small className="text-site-muted">You play the patient</small></span>
          </div>
        </Cell>
        <Cell className="border-site-line bg-site-card md:col-span-2">
          <div className="flex items-center gap-3">
            <Image src={ATHENA_IMAGE_SRC} alt="Athena, your AI tutor" width={44} height={44} className="h-11 w-11 shrink-0 rounded-full object-cover" />
            <div>
              <h3 className="font-landing-heading text-xl font-bold text-site-ink">Debrief with Athena</h3>
              <span className="text-xs text-site-muted">Ready after every case</span>
            </div>
          </div>
          <p className="mt-3 text-site-body">Your AI tutor after every case, walking through communication and management outlines.</p>
          <div aria-hidden="true" className="mt-5 flex flex-col gap-2">
            <span className={BUBBLE}>At 1:20 she mentioned blurred vision. What could that point to?</span>
            <span className={BUBBLE_ME}>Raised pressure. I should have asked.</span>
            <span className="flex gap-1 self-start rounded-2xl bg-site-pale px-4 py-3">
              {[0, 1, 2].map((i) => (
                <i key={i} className="site-dot h-1.5 w-1.5 rounded-full bg-site-brand" style={{ animationDelay: `${i * 0.2}s` }} />
              ))}
            </span>
          </div>
        </Cell>
        <Cell className="border-transparent bg-site-brand text-site-on-brand md:col-span-2">
          <span aria-hidden="true" className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-white/15 text-xl"><FiClock /></span>
          <span className="mt-4 font-landing-mono text-[11px] font-medium uppercase tracking-[0.13em]">On the clock</span>
          <h3 className="mt-2 font-landing-heading text-xl font-bold">Timed like the real exam</h3>
          <p className="mt-2 opacity-90">Reading and consultation timers match your exam, with extra time if you need it.</p>
          <div aria-hidden="true" className="mt-5">
            <HomeClock from={708} className="font-landing-mono text-5xl font-medium" />
          </div>
        </Cell>
      </div>
    </Section>
  );
}

const EXAMS = [
  { href: "/exams/sca", code: "SCA", name: "Structured Clinical Assessment", Icon: FaUserDoctor },
  { href: "/exams/plab", code: "PLAB 2", name: "Professional and Linguistic Assessment", Icon: FiGlobe },
  { href: "/exams/casc", code: "CASC", name: "Clinical Assessment of Skills and Competencies", Icon: FiHeart },
  { href: "/exams/ortho", code: "Orthopaedics", name: "ST3 Interview", Icon: GiBoneKnife },
] as const;

export function HomeExams() {
  return (
    <Section id="exams" tone="card">
      <SectionHead title="Choose your exam" sub="Select your exam pathway and start practising with our AI-powered stations." />
      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {EXAMS.map(({ href, code, name, Icon }, i) => (
          <Link
            key={code}
            href={href}
            className={`group flex flex-col rounded-2xl border p-6 transition-colors hover:border-site-brand ${
              i === 0 ? "border-site-brand bg-site-pale" : "border-site-line bg-site-ground"
            }`}
          >
            <IconTile><Icon /></IconTile>
            <span className="mt-4 font-landing-heading text-2xl font-bold text-site-ink">{code}</span>
            <span className="mt-1 flex-1 text-sm text-site-body">{name}</span>
            <span className="mt-4 text-sm font-semibold text-site-brand">Start practising →</span>
          </Link>
        ))}
      </div>
    </Section>
  );
}
