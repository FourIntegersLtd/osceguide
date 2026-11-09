import type { QuoteCardData } from "@/domains/marketing/home/QuoteCard";
import { MARQUEE_TESTIMONIALS } from "@/domains/marketing/support/testimonials";

/** The copy of `/`, as the page read before its redesign. */
export const HERO = {
  lead: "OSCE Guide transforms the way healthcare professionals prepare for their clinical simulation exams. Our Voice AI-powered platform simulates real patient interactions, helping you sharpen your clinical skills and enhance communication.",
  cta: "Start free",
  contact: "Contact us",
} as const;

const byName = (names: readonly string[]): readonly QuoteCardData[] =>
  names.map((name) => {
    const t = MARQUEE_TESTIMONIALS.find((m) => m.name === name);
    if (!t) throw new Error(`landing quote missing from MARQUEE_TESTIMONIALS: ${name}`);
    return { name: t.name, role: t.role, text: t.excerpt, highlight: t.highlight };
  });

/** Under the hero. */
export const PROOF_QUOTES = byName(["Dr C.O", "Dr R", "Dr Nazia Qadeer"]);

export const STEPS = {
  eyebrow: "How it works",
  title: "Pick a case. Talk to the patient. See your marks.",
  items: [
    { title: "Pick the number of cases you would like to do" },
    { title: "Speak to an AI patient that responds like a real human" },
    { title: "Get structured feedback and debrief with our custom tutor Athena" },
  ],
} as const;

export const FEATURES = {
  feedback: {
    eyebrow: "Your feedback",
    title: "See exactly where you lost the mark.",
    body: "Every case comes back marked on the same domains the examiners use, so you know what to change next time, not just your score.",
    checks: [
      "Marked on the domains your exam uses",
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
    title: "Practise with a real person, on your schedule",
    items: [
      { title: "Live Practice", body: "Get matched instantly with available colleagues and start practising immediately." },
      { title: "Marketplace", body: "Post your availability or browse sessions from colleagues. Schedule at times that work for both of you." },
      { title: "Automatic Timing", body: "Built-in timer matches the exam format. Practise with realistic time constraints." },
    ],
  },
  timing: {
    title: "Extra time when you need it",
    body: "OSCE Guide is built to be inclusive. Turn on Extra Time in your Profile and every station uses your chosen durations. No questions asked.",
    checks: [
      "Extra Time for neurodiverse learning needs",
      "Set your own reading and simulation timers to match your exam arrangements",
    ],
  },
} as const;

export const EXAMS = {
  title: "Choose your exam",
  sub: "Select your exam pathway and start practising with our AI-powered stations.",
  items: [
    { href: "/exams/sca", code: "SCA", name: "Structured Clinical Assessment" },
    { href: "/exams/plab", code: "PLAB 2", name: "Professional and Linguistic Assessment" },
    { href: "/exams/casc", code: "CASC", name: "Clinical Assessment of Skills and Competencies" },
    { href: "/exams/ortho", code: "Orthopaedics", name: "ST3 Interview" },
  ],
  start: "Start practising →",
} as const;

export const PRICING = {
  eyebrow: "Pricing",
  title: "Try it free. Then pay for the months you need.",
  sub: "Every paid plan has every case for your exam, three attempts at each, and Athena for the debrief.",
} as const;

/** From the institutions page: its hero and its closing call to action. */
export const INSTITUTIONS = {
  title: "Run training & exam days with virtual patients",
  body: "OSCE Guide helps institutions run OSCE training sessions and full exam days with virtual patients. Candidates get more time to practise, faculty spend less time on setup, and sessions stay on schedule.",
  link: "Institutions",
  demo: "Book a demo",
} as const;

export const FOUNDERS = {
  eyebrow: "A message from our founders",
  signoff: { names: "Kenny and Aisha", role: "Co-founders" },
} as const;
