import type { QuoteCardData } from "@/domains/marketing/home/QuoteCard";
import { MARQUEE_TESTIMONIALS } from "@/domains/marketing/support/testimonials";
import { FREE_TRIAL_DAYS } from "@/foundation/config/copyNumbers";

/** The approved copy of `/`. */
export const FREE_TRIAL = `Free for ${FREE_TRIAL_DAYS} days. No card.`;

export const HERO = {
  eyebrow: "For doctors sitting the SCA, PLAB 2, CASC or ST3 interview",
  title: "Practise your exam cases out loud with an AI patient.",
  titleTail: "No study partner needed.",
  lead: `Pick a case, talk to the patient for the exam's real time, and get marked on each domain the way the examiners mark. ${FREE_TRIAL}`,
  cta: "Try a case free",
  sample: "See what the feedback looks like",
  proofQuote: "I passed on 1st attempt.",
  proofName: "Dr Elizabeth Okuonghae",
} as const;

const byName = (names: readonly string[]): readonly QuoteCardData[] =>
  names.map((name) => {
    const t = MARQUEE_TESTIMONIALS.find((m) => m.name === name);
    if (!t) throw new Error(`landing quote missing from MARQUEE_TESTIMONIALS: ${name}`);
    return { name: t.name, role: t.role, text: t.landing?.text ?? t.excerpt.replaceAll("@OSCEGuide", "OSCE Guide"), highlight: t.landing?.highlight ?? t.highlight };
  });

/** Under the hero: three who are not the hero's own quote. */
export const PROOF_QUOTES = byName(["Dr C.O", "Dr R", "Dr Nazia Qadeer"]);

export const STORIES = byName(["Dr Elizabeth Okuonghae", "Dr Nazia Qadeer", "Dr Adeleke", "Dr S", "Dr Marion Ogunmola", "Dr Zahra"]);

export const STEPS = {
  eyebrow: "How it works",
  title: "Pick a case. Talk to the patient. See your marks.",
  sub: "Nothing to install. It runs in your browser, on your phone or your laptop.",
  items: [
    { title: "Pick a case", body: "Choose from the cases for your exam. Or let us pick one, like a mock would." },
    { title: "Talk to the patient", body: "Speak as you would in the exam. The patient answers like a real one, and the clock runs for the exam's real time." },
    { title: "See your marks", body: "Your score in each domain, and the line in your transcript that won or lost it. Then talk it through with Athena." },
  ],
} as const;

export const FEATURES = {
  feedback: {
    eyebrow: "Your feedback",
    title: "See exactly where you lost the mark.",
    body: "Every case comes back marked on the same domains the examiners use. Click a mark and you'll see the line in your transcript it came from. So you know what to change next time, not just your score.",
    checks: [
      "Marked on data gathering, clinical management and relating to others",
      "Every mark points to a line in your transcript",
      "Your scores over time, domain by domain",
    ],
  },
  athena: {
    eyebrow: "Athena",
    title: "Talk it through afterwards.",
    body: "When the case ends, Athena goes over what you missed and how she'd have handled it. Ask her anything about the case while it's still fresh.",
    quote: { text: "I gained from the feedback from Athena and also acted as the patient so I could see how she will handle some cases.", name: "Dr I.O", role: "Passed SCA" },
  },
  colleagues: {
    eyebrow: "Practice with colleagues",
    title: "Want a real person? Match with one.",
    body: "Match with another doctor now, or post a time in the marketplace. You run the same cases on the same clock, and take turns being the patient.",
    link: "See how matching works",
  },
  timing: {
    eyebrow: "Timing",
    title: "The exam's clock. And your extra time, if you get it.",
    body: "Reading time and talking time match your exam. If you get extra time in the real thing, switch on Extra Time once and every case uses it. You can set your own times too.",
    checks: [
      "Same reading and talking time as your exam",
      "One switch for extra time. No forms, no questions",
      "Or set your own times to train slower or faster",
    ],
  },
} as const;

export const EXAMS = {
  eyebrow: "Exams",
  title: "Pick your exam.",
  sub: "The cases are written by doctors who've sat it, and marked the way it's marked.",
  items: [
    { href: "/exams/sca", code: "SCA", body: "MRCGP, UK", line: "Phone and face-to-face cases across the RCGP curriculum." },
    { href: "/exams/plab", code: "PLAB 2", body: "GMC, UK", line: "History, explaining and management stations, eight minutes each." },
    { href: "/exams/casc", code: "CASC", body: "MRCPsych", line: "Psychiatric history, risk and mental state stations, including linked pairs." },
    { href: "/exams/ortho", code: "Ortho ST3", body: "Trauma and Orthopaedics interview", line: "Clinical, prioritisation and portfolio stations for the national interview." },
  ],
  start: "Start practising →",
} as const;

export const STORIES_HEAD = { eyebrow: "Stories", title: "What doctors say." } as const;

export const PRICING = {
  eyebrow: "Pricing",
  title: "Try it free. Then pay for the months you need.",
  sub: "Every paid plan has every case for your exam, three attempts at each, and Athena for the debrief.",
} as const;

export const INSTITUTIONS = {
  eyebrow: "For training programmes, trusts and employers",
  title: "Run your own OSCE here.",
  body: "Set up the circuit, invite your candidates and examiners, and mark with the same engine your trainees practise on. Every result in one place. Employers use the same thing for interview stations.",
  link: "OSCE Guide for institutions",
  demo: "Book a demo",
} as const;

export const FAQ_HEAD = { eyebrow: "Questions", title: "Things people ask us.", sub: "Anything else? Email", subTail: "A person replies, usually the same day." } as const;

export const FOUNDERS = { eyebrow: "A note from the founders", signoff: "The founders · OSCE Guide" } as const;

export const FINAL = {
  title: "Your next case is waiting.",
  sub: `Free for ${FREE_TRIAL_DAYS} days. No card needed. Nothing to cancel.`,
  demo: "Book a demo for your programme",
} as const;
