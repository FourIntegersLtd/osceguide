import { VISIBLE_EXAMS } from "@/domains/marketing/pricingContent";

/** The copy of `/`, as the page read before its redesign. */
export const HERO = {
  lead: "OSCE Guide transforms the way healthcare professionals prepare for their clinical simulation exams. Our Voice AI-powered platform simulates real patient interactions, helping you sharpen your clinical skills and enhance communication.",
  cta: "Start free",
  contact: "Contact us",
} as const;

/** The `#how` section's heading and three steps; `CLOSING.title` reuses its headline. */
export const HOW_IT_WORKS = {
  eyebrow: "How it works",
  title: "Pick a case. Talk to the patient. See your marks.",
  items: [
    { title: "Pick the number of cases you would like to do" },
    { title: "Speak to an AI patient that responds like a real human" },
    { title: "Get structured feedback and debrief with our custom tutor Athena" },
  ],
} as const;

/** The headline of the closing band. */
export const CLOSING = { title: HOW_IT_WORKS.title } as const;

export const FEATURES = {
  feedback: {
    eyebrow: "Your feedback",
    title: "Your transcript, marked line by line.",
    body: "Every case comes back marked on the same domains the examiners use, so you know what to change next time, not just your score.",
    items: [
      { title: "Marked on the domains your exam uses", body: "Structured feedback aligned with your exam\u2019s marking domains." },
      { title: "Every mark points to a line in your transcript", body: "Real-Time Speech Transcription." },
      { title: "Your scores over time, domain by domain", body: "In-Depth Performance Analytics." },
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
  /** Every exam the page has copy for; `VISIBLE_EXAM_ITEMS` picks which show. */
  items: [
    { key: "SCA", href: "/exams/sca", code: "SCA", name: "Structured Clinical Assessment" },
    { key: "PLAB", href: "/exams/plab", code: "PLAB 2", name: "Professional and Linguistic Assessment" },
    { key: "CASC", href: "/exams/casc", code: "CASC", name: "Clinical Assessment of Skills and Competencies" },
    { key: "ORTHO", href: "/exams/ortho", code: "Orthopaedics", name: "ST3 Interview" },
  ],
  start: "Start practising →",
} as const;

/** The institutions line on `/`. */
export const INSTITUTIONS = {
  title: "Run training & exam days with virtual patients",
  link: "Institutions",
  demo: "Book a demo",
} as const;

/** The exam cards shown on `/`: `EXAMS.items` limited to `VISIBLE_EXAMS`. */
export const VISIBLE_EXAM_ITEMS = EXAMS.items.filter((exam) => VISIBLE_EXAMS.includes(exam.key));
