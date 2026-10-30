"use client";

import type { CSSProperties } from "react";
import { HiOutlineUser } from "react-icons/hi2";
import { LuStethoscope } from "react-icons/lu";

import {
  PRIORITISATION_SHOWCASE_CONTENT,
  SIMULATION_SHOWCASE_CONTENT,
  type ExamShowcaseVariant,
} from "./examShowcaseContent";

const WAVEFORM_DELAYS = ["0s", "0.1s", "0.2s", "0.3s", "0.15s"];

function HeroWaveform() {
  return (
    <div className="flex h-4 items-center gap-1" aria-hidden>
      {WAVEFORM_DELAYS.map((delay) => (
        <span
          key={delay}
          className="voice-memo-bar h-full w-[2.5px] rounded-sm bg-site-brand"
          style={{ animationDelay: delay }}
        />
      ))}
    </div>
  );
}

type LandingSimulationShowcaseProps = {
  variant: ExamShowcaseVariant;
};

export function LandingSimulationShowcase({
  variant,
}: LandingSimulationShowcaseProps) {
  const content = SIMULATION_SHOWCASE_CONTENT[variant];

  return (
    <div className="mx-auto w-full overflow-hidden rounded-2xl border border-site-line bg-site-card shadow-sm sm:rounded-2xl lg:w-4/5">
      <div className="h-[3px] bg-site-line" aria-hidden>
        <i className="block h-full w-[42%] bg-site-brand" />
      </div>
      <div className="flex flex-col lg:min-h-[420px] lg:flex-row">
        <div className="min-w-0 flex-1 border-b border-site-line p-5 sm:p-6 lg:flex lg:flex-col lg:border-b-0 lg:border-r lg:px-7 lg:py-8">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-4 lg:mb-6">
            <div>
              <div className="font-landing-mono text-[10px] font-medium uppercase tracking-[0.13em] text-site-faint">
                {content.examLabel}
              </div>
              <div className="mt-1 font-landing-heading text-lg font-semibold leading-[1.3] tracking-[-0.02em] text-site-ink sm:text-[19px]">
                {content.stationTitle}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <HeroWaveform />
              <span className="font-landing-mono text-xs text-site-body">
                {content.timerLabel}
              </span>
            </div>
          </div>
          <div className="flex flex-col gap-3 lg:flex-1 lg:justify-center lg:gap-3.5">
            {content.transcriptRows.map((row) => {
              const isCandidate = row.side === "you";

              return (
                <div
                  key={row.time}
                  className={`flex items-end gap-2 ${
                    isCandidate ? "justify-end" : "justify-start"
                  }`}
                >
                  {!isCandidate && (
                    <span
                      className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-site-line bg-site-pale text-site-body"
                      aria-hidden
                    >
                      <HiOutlineUser className="h-3.5 w-3.5" />
                    </span>
                  )}

                  <div
                    className={`max-w-[84%] rounded-[14px] border px-3.5 py-2.5 sm:max-w-[78%] ${
                      isCandidate
                        ? "rounded-br-[4px] border-site-rule bg-site-pale"
                        : "rounded-bl-[4px] border-site-line bg-site-pale"
                    }`}
                  >
                    <div
                      className={`flex items-baseline gap-2 ${
                        isCandidate ? "justify-end" : ""
                      }`}
                    >
                      <span
                        className={`font-landing-mono text-[10.5px] font-medium uppercase tracking-[0.06em] ${
                          isCandidate
                            ? "text-site-brand"
                            : "text-site-body"
                        }`}
                      >
                        {row.speaker}
                      </span>
                      <span className="font-landing-mono text-[10.5px] text-site-muted">
                        {row.time}
                      </span>
                    </div>
                    <p className="mt-1 font-landing-body text-sm leading-[1.55] text-site-ink sm:text-[15px]">
                      {row.text}
                    </p>
                  </div>

                  {isCandidate && (
                    <span
                      className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-site-rule bg-site-brand text-site-on-brand"
                      aria-hidden
                    >
                      <LuStethoscope className="h-3.5 w-3.5" />
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="min-w-0 bg-site-pale p-5 sm:p-6 lg:flex lg:w-[34%] lg:shrink-0 lg:flex-col lg:justify-center lg:px-6 lg:py-8">
          <div className="mb-4 font-landing-mono text-[10px] font-medium uppercase tracking-[0.13em] text-site-faint lg:mb-5">
            {content.checklistEyebrow}
          </div>
          <div className="flex flex-col gap-2.5 lg:gap-3">
            {content.checklistItems.map((item, index) => {
              // Index drives the stagger; `done` is the reduced-motion fallback.
              const tickVars = {
                "--landing-tick-index": index,
                "--landing-tick-static-opacity": item.done ? 1 : 0,
              } as CSSProperties;

              return (
                <div
                  key={item.label}
                  className="flex items-start gap-2"
                  style={tickVars}
                >
                  <span
                    className={`landing-checklist-item landing-checklist-box mt-0.5 flex h-[15px] w-[15px] shrink-0 items-center justify-center rounded border ${
                      item.done
                        ? "border-osce-band-competentBorder bg-osce-band-competentBg"
                        : "border-site-rule bg-site-card"
                    }`}
                    aria-hidden
                  >
                    <svg
                      viewBox="0 0 12 12"
                      className="landing-checklist-item landing-checklist-mark h-[9px] w-[9px]"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.25"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      style={{ color: "var(--osce-band-competent)" }}
                    >
                      <path d="M2.5 6.4 4.9 8.8 9.5 3.6" />
                    </svg>
                  </span>
                  <span
                    className={`landing-checklist-item landing-checklist-label font-landing-body text-[13px] leading-[1.45] ${
                      item.done ? "text-site-body" : "text-site-muted"
                    }`}
                  >
                    {item.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export function LandingPrioritisationShowcase() {
  const content = PRIORITISATION_SHOWCASE_CONTENT;

  return (
    <div className="overflow-hidden rounded-2xl border border-site-line bg-site-card shadow-sm">
      <div className="border-b border-site-line px-5 py-4 sm:px-6 sm:py-5">
        <div className="font-landing-mono text-[10px] font-medium uppercase tracking-[0.13em] text-site-muted">
          Prioritisation station
        </div>
        <h3 className="mt-1.5 font-landing-heading text-lg font-semibold tracking-[-0.02em] text-site-ink sm:text-xl">
          {content.title}
        </h3>
        <p className="mt-1 font-landing-body text-sm text-site-body">
          {content.subtitle}
        </p>
      </div>

      <ol className="divide-y divide-site-line">
        {content.cases.map((item) => (
          <li
            key={item.rank}
            className="flex items-start gap-4 px-5 py-4 sm:px-6 sm:py-5"
          >
            <span
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg font-landing-mono text-sm font-medium ${
                item.urgent
                  ? "bg-site-pale text-site-brand"
                  : "bg-site-pale text-site-body"
              }`}
            >
              {item.rank}
            </span>
            <div className="min-w-0">
              <p className="font-landing-body text-sm font-medium text-site-ink sm:text-[15px]">
                {item.label}
              </p>
              <p className="mt-1 font-landing-body text-sm leading-relaxed text-site-body">
                {item.detail}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
