import type { IconType } from "react-icons";
import {
  HiOutlineChartBar,
  HiOutlineClipboardDocumentCheck,
  HiOutlineMicrophone,
  HiOutlinePlayCircle,
  HiOutlineSparkles,
  HiOutlineUserGroup,
  HiOutlineVideoCamera,
} from "react-icons/hi2";
import type { LandingIconColor } from "@/domains/marketing/landingIconPalette";

export const DEMO_MAILTO =
  "mailto:hello@fourintegers.com?subject=OSCE%20Guide%20Institutions%20Demo";

export const INSTITUTIONS_NAV = [
  { href: "#for", label: "Who it's for" },
  { href: "#how", label: "How it works" },
  { href: "#contact", label: "Contact" },
] as const;

export const B2B_IMG = {
  dashboard: { src: "/images/b2b/b2b-dashboard.png", w: 2458, h: 1704 },
} as const;

export const VALUE_PROPS: Array<{
  label: string;
  body: string;
  icon: IconType;
  iconColor: LandingIconColor;
}> = [
  {
    label: "More practice for every candidate",
    body:
      "Every candidate gets the same virtual patient in a circuit. Schedule around your timetable, not actor availability.",
    icon: HiOutlineMicrophone,
    iconColor: "cyan",
  },
  {
    label: "Simple to run for faculty",
    body:
      "Set up cohorts, stations, and running order in minutes. Supervisors monitor live and score against your rubrics.",
    icon: HiOutlineClipboardDocumentCheck,
    iconColor: "blue",
  },
  {
    label: "Progress you can review",
    body:
      "Consultations, feedback, and supervisor notes in one place. Track performance across stations and cohorts.",
    icon: HiOutlineChartBar,
    iconColor: "indigo",
  },
];

export const HOW_IT_WORKS_STEPS: Array<{
  step: string;
  title: string;
  body: string;
  icon: IconType;
  iconColor: LandingIconColor;
}> = [
  {
    step: "Step 1",
    title: "Candidate joins station",
    body: "Each candidate enters the circuit on schedule and connects to their assigned virtual patient.",
    icon: HiOutlineUserGroup,
    iconColor: "blue",
  },
  {
    step: "Step 2",
    title: "Voice consultation",
    body: "The candidate consults the virtual patient by voice, just as they would on exam day.",
    icon: HiOutlineMicrophone,
    iconColor: "cyan",
  },
  {
    step: "Step 3",
    title: "Structured feedback",
    body: "Feedback is recorded against your marking criteria and stored for review.",
    icon: HiOutlineClipboardDocumentCheck,
    iconColor: "indigo",
  },
  {
    step: "Step 4",
    title: "Faculty oversight",
    body: "Supervisors observe in real time and can intervene or take notes during training sessions.",
    icon: HiOutlineVideoCamera,
    iconColor: "teal",
  },
];

export const BUYER_TYPES = [
  {
    label: "Academic Programmes",
    description:
      "Every candidate practises with the same virtual patient. Ideal for skills weeks or one-off training sessions.",
    examples: [
      "Medical schools",
      "Nursing programmes",
      "Paramedic training",
      "Allied health programmes",
    ],
  },
  {
    label: "Postgraduate & Workforce Training",
    description:
      "Foundation, GP, specialty, and employer training with group practice and assessment days in one place.",
    examples: [
      "GP training",
      "Foundation programmes",
      "Specialty training",
      "Employer training",
    ],
  },
] as const;

export const PLATFORM_FEATURES: Array<{
  text: string;
  icon: IconType;
  iconColor: LandingIconColor;
}> = [
  {
    icon: HiOutlineSparkles,
    iconColor: "violet",
    text: "Virtual patients built from your station briefs",
  },
  {
    icon: HiOutlineVideoCamera,
    iconColor: "cyan",
    text: "Live voice consultations supervisors can observe in real time",
  },
  {
    icon: HiOutlinePlayCircle,
    iconColor: "orange",
    text: "Training and assessment modes with faculty oversight",
  },
  {
    icon: HiOutlineClipboardDocumentCheck,
    iconColor: "indigo",
    text: "Feedback forms and marking criteria you configure",
  },
];

export const TRAINING_BULLETS = [
  "Supervisor-controlled circuit timing",
  "Live notes at each station",
  "Reusable layouts per cohort",
  "Feedback after every station",
] as const;

export const EXAM_BULLETS = [
  "Supervisor oversight, no intervention",
  "Identical virtual patients per candidate",
  "Examiner approval before release",
  "Full supervisor audit trail",
] as const;
