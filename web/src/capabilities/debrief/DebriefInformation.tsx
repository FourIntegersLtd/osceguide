"use client";

import { HiChatAlt2, HiLightBulb, HiRefresh, HiSparkles } from "react-icons/hi";
import {
  cn,
  productTokens,
} from "@/foundation/ui";
import { useCurrentExam, hasStationSubtypes } from "@/foundation/session";
import { DEBRIEF_HEADING, DEBRIEF_INTRO } from "./debriefCopy";

const {
  b2cGroupedRow,
  b2cGroupedRowSubtitle,
  b2cGroupedRowTitle,
  b2cCard,
} = productTokens;

const DEFAULT_FEATURES = [
  {
    icon: <HiChatAlt2 className="h-5 w-5 text-osce-accent" aria-hidden />,
    title: "Live Analysis",
    desc: "Discuss specific moments from your transcript with Athena to understand exactly where improvements can be made.",
    bg: "bg-osce-accent-muted",
  },
  {
    icon: <HiLightBulb className="h-5 w-5 text-osce-warning-text" aria-hidden />,
    title: "Targeted Tips",
    desc: "Get actionable advice on ICE, clinical reasoning, and safety-netting tailored to your performance.",
    bg: "bg-osce-warning-bg",
  },
  {
    icon: <HiRefresh className="h-5 w-5 text-osce-success-text" aria-hidden />,
    title: "Active Practice",
    desc: "Role-play challenging sections again to perfect your wording and confidence in real-time.",
    bg: "bg-osce-success-bg",
  },
];

const ORTHO_FEATURES = [
  {
    icon: <HiChatAlt2 className="h-5 w-5 text-osce-accent" aria-hidden />,
    title: "Clinical & Imaging Discussion",
    desc: "Discuss your radiograph interpretation, key concerns, and clinical reasoning. Compare your approach to BOAST/NICE and the expected interview answers.",
    bg: "bg-osce-accent-muted",
  },
  {
    icon: <HiLightBulb className="h-5 w-5 text-osce-warning-text" aria-hidden />,
    title: "Station-Specific Feedback",
    desc: "Clinical: technical knowledge and management. Prioritisation: list ordering and BOAST. Communication: consent, SPIKES, duty of candour. Portfolio: CAMP, person spec, NJR/GIRFT, reflection.",
    bg: "bg-osce-warning-bg",
  },
  {
    icon: <HiRefresh className="h-5 w-5 text-osce-success-text" aria-hidden />,
    title: "Practice & Role-play",
    desc: "Rehearse difficult questions, rephrase management plans, or practise portfolio answers with Athena.",
    bg: "bg-osce-success-bg",
  },
];

const DEFAULT_STEPS = [
  {
    step: "01",
    title: "Review Your Transcript",
    text: "Athena has read your session. Ask her to pinpoint exactly where you could improve your exploration or management.",
  },
  {
    step: "02",
    title: "Ask Specific Questions",
    text: "Instead of 'How did I do?', try 'Can we look at my red-flag checks?' Or 'Was my safety-netting clear enough?'",
  },
  {
    step: "03",
    title: "Engage in Role-play",
    text: "Ask Athena to practise a specific difficult moment again. She can play the patient while you refine your approach.",
  },
];

const ORTHO_STEPS = [
  {
    step: "01",
    title: "Review Transcript & Feedback",
    text: "Athena has your transcript and station feedback. Ask her to highlight where your imaging interpretation, key concerns, or interview answers matched or missed the expected standard.",
  },
  {
    step: "02",
    title: "Ask Station-Relevant Questions",
    text: "Clinical: 'Where could my management align better with BOAST?' Prioritisation: 'How could my list order have been stronger?' Communication: 'Was my consent/SPIKES approach clear?'",
  },
  {
    step: "03",
    title: "Practice Key Moments",
    text: "Role-play rephrasing a management plan, defending a prioritisation order, or answering a portfolio question with Athena.",
  },
];

const DEFAULT_SUGGESTED_PROMPTS = [
  "Can we discuss examples of missed ICE/cue responses?",
  "How did my red flag checks align with the management plan?",
  "Could my plan have been more collaborative? How can I improve?",
  "Were my explanations and safety-netting clear enough?",
  "Let's role-play how I could have handled that challenging question.",
];

const ORTHO_SUGGESTED_PROMPTS = [
  "Where could my imaging interpretation or key concerns have been stronger?",
  "How did my management align with BOAST/NICE and the expected answers?",
  "Can we go through the interview questions I missed or could improve?",
  "How could my list order or consent/SPIKES approach have been clearer?",
  "For portfolio stations, how could I better link my CV to the person specification?",
];

export function DebriefTips() {
  const { settings } = useCurrentExam();
  const ortho = hasStationSubtypes(settings);
  const features = ortho ? ORTHO_FEATURES : DEFAULT_FEATURES;
  const steps = ortho ? ORTHO_STEPS : DEFAULT_STEPS;

  return (
    <div className="mx-auto w-full max-w-3xl py-2">
      <div className="mb-4 space-y-2 text-center">
        <div className="inline-flex items-center gap-1.5 rounded-md border border-osce-accent-subtle bg-osce-accent-muted px-3 py-1 text-osce-caption font-semibold uppercase tracking-wider text-osce-accent">
          <HiSparkles className="h-3 w-3" aria-hidden /> Powered by Athena
        </div>
        <h2 className="text-osce-body font-semibold tracking-tight text-osce-ink-900">
          {ortho ? DEBRIEF_HEADING.ortho : DEBRIEF_HEADING.default}
        </h2>
        <p className="mx-auto max-w-xl text-osce-body leading-relaxed text-b2c-text-muted">
          {ortho ? DEBRIEF_INTRO.ortho : DEBRIEF_INTRO.default}
        </p>
      </div>

      <div className={cn("mb-4 overflow-hidden", b2cCard)}>
        {features.map((item) => (
          <div key={item.title} className={b2cGroupedRow}>
            <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg", item.bg)}>
              {item.icon}
            </div>
            <div className="min-w-0 flex-1 space-y-0.5">
              <h4 className={b2cGroupedRowTitle}>{item.title}</h4>
              <p className={b2cGroupedRowSubtitle}>{item.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        <h3 className="text-center text-osce-body font-semibold tracking-tight text-osce-ink-900">
          How to get the most out of it
        </h3>
        <div className="grid grid-cols-1 gap-2.5">
          {steps.map((item) => (
            <div
              key={item.step}
              className="flex gap-3 rounded-lg border border-b2c-border-light bg-b2c-surface-muted/50 p-3"
            >
              <span className="text-osce-body font-semibold tabular-nums text-b2c-text-muted">
                {item.step}
              </span>
              <div className="space-y-0.5">
                <h4 className="text-osce-body font-semibold text-osce-ink-900">{item.title}</h4>
                <p className="text-osce-meta leading-relaxed text-b2c-text-muted">{item.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <p className="mt-6 text-center text-osce-meta font-medium text-b2c-text-muted">
        Athena is designed to support your learning. Every session counts.
      </p>
    </div>
  );
}

export function DebriefSuggestedPrompts() {
  const { settings } = useCurrentExam();
  const prompts = hasStationSubtypes(settings) ? ORTHO_SUGGESTED_PROMPTS : DEFAULT_SUGGESTED_PROMPTS;

  return (
    <div className="space-y-3">
      <div className="mb-1 flex items-center gap-1.5">
        <HiLightBulb className="h-3.5 w-3.5 text-osce-accent" aria-hidden />
        <h4 className="text-osce-meta font-semibold uppercase tracking-wider text-b2c-text-muted">
          Suggested Prompts for Athena
        </h4>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {prompts.map((prompt) => (
          <div
            key={prompt}
            className={cn(
              "group flex cursor-default items-center gap-1.5 px-3 py-1.5 text-osce-meta text-b2c-text-secondary transition-colors hover:border-osce-accent hover:text-osce-accent-hover",
              b2cCard,
            )}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-osce-accent-subtle transition-colors group-hover:bg-osce-accent-hover" />
            {prompt}
          </div>
        ))}
      </div>
    </div>
  );
}
