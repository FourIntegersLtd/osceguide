"use client";

import { LuStethoscope } from "react-icons/lu";
import { HiOutlineCheck } from "react-icons/hi2";
import { useEffect, useState, type ReactNode } from "react";
import Image from "next/image";
import { AnimatePresence, motion } from "framer-motion";
import { ATHENA_IMAGE_SRC } from "@/foundation/ui/AthenaIdentity";
import { VoiceMemoBars } from "./VoiceMemoBars";

const TRANSCRIPT_LINES = [
  { role: "Patient" as const, text: "The pain started about three days ago." },
  { role: "You" as const, text: "Can you describe what it feels like?" },
  { role: "Patient" as const, text: "It's a sharp pain when I breathe in." },
  { role: "You" as const, text: "Any fever, cough, or recent travel?" },
  { role: "Patient" as const, text: "No fever, but I have felt more tired." },
  { role: "You" as const, text: "Let me explore your history further." },
  { role: "Patient" as const, text: "It gets worse when I lie flat." },
  { role: "You" as const, text: "Have you noticed any leg swelling?" },
];

const CALENDAR_DAYS = ["M", "T", "W", "T", "F", "S", "S"];
const CALENDAR_CELLS = Array.from({ length: 28 }, (_, index) => index + 1);

const SHOWCASE_SLIDES = [
  { id: "voice", label: "AI voice consultation" },
  { id: "marketplace", label: "Marketplace booking" },
  { id: "institution", label: "Institution training" },
] as const;

const SHOWCASE_VIEWPORT_CLASS =
  "landing-showcase-viewport relative h-[28rem] overflow-hidden sm:h-[34rem] lg:h-[38rem]";

type ShowcaseSceneProps = {
  children: ReactNode;
  className?: string;
};

function ShowcaseScene({ children, className = "" }: ShowcaseSceneProps) {
  return (
    <div className={`landing-showcase-scene ${className}`}>{children}</div>
  );
}

type ShowcaseSceneHeaderProps = {
  children: ReactNode;
  className?: string;
};

function ShowcaseSceneHeader({ children, className = "" }: ShowcaseSceneHeaderProps) {
  return (
    <div className={`landing-showcase-scene-header ${className}`}>{children}</div>
  );
}

type ShowcaseSceneBodyProps = {
  children: ReactNode;
  className?: string;
};

function ShowcaseSceneBody({ children, className = "" }: ShowcaseSceneBodyProps) {
  return (
    <div className={`landing-showcase-scene-body ${className}`}>{children}</div>
  );
}

function TranscriptBubble({
  role,
  text,
}: {
  role: "Patient" | "You";
  text: string;
}) {
  const isYou = role === "You";

  return (
    <div className={`flex ${isYou ? "justify-end" : "justify-start"}`}>
      <div
        className={`showcase-bubble max-w-[min(100%,22rem)] shadow-sm sm:rounded-2xl sm:px-4 sm:py-3 ${
          isYou
            ? "rounded-br-md border border-osce-accent/30 bg-osce-accent-muted text-neutral-800"
            : "rounded-bl-md border border-slate-200/80 bg-white text-neutral-800"
        }`}
      >
        <p
          className={`showcase-bubble-role font-landing-body font-semibold uppercase tracking-[0.1em] sm:text-[11px] ${
            isYou ? "text-osce-accent" : "text-neutral-500"
          }`}
        >
          {role}
        </p>
        <p
          className="showcase-bubble-text font-landing-body mt-0.5 leading-relaxed text-neutral-700 sm:mt-1 sm:text-sm lg:text-base"
        >
          {text}
        </p>
      </div>
    </div>
  );
}

function VoiceConsultationScene() {
  return (
    <ShowcaseScene className="bg-gradient-to-br from-slate-50 to-osce-accent-muted/20 sm:p-8 lg:p-10">
      <ShowcaseSceneHeader className="mb-2 lg:hidden sm:mb-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-col items-center">
            <div className="showcase-avatar relative overflow-hidden rounded-full border-2 border-white bg-white shadow-md sm:h-16 sm:w-16 sm:border-4">
              <Image
                src={ATHENA_IMAGE_SRC}
                alt=""
                fill
                className="object-cover object-top"
                sizes="64px"
              />
            </div>
            <p className="showcase-avatar-label font-landing-body font-semibold text-neutral-700 sm:text-xs">
              Patient
            </p>
          </div>
          <div className="flex flex-col items-center">
            <div className="showcase-avatar relative overflow-hidden rounded-full border-2 border-white bg-white shadow-md sm:h-16 sm:w-16 sm:border-4">
              <Image
                src="/images/landing/hero-doctor.png"
                alt=""
                fill
                className="object-cover object-top"
                sizes="64px"
              />
            </div>
            <p className="showcase-avatar-label font-landing-body font-semibold text-neutral-700 sm:text-xs">
              You
            </p>
          </div>
        </div>
      </ShowcaseSceneHeader>

      <ShowcaseSceneBody>
        <div className="grid h-full min-h-0 gap-2 sm:gap-5 lg:grid-cols-[minmax(7.5rem,9rem)_1fr_minmax(7.5rem,9rem)] lg:items-stretch lg:gap-6">
          <div className="hidden flex-col items-center justify-center rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-sm lg:flex">
            <div className="relative h-24 w-24 overflow-hidden rounded-full border-4 border-white shadow-md xl:h-28 xl:w-28">
              <Image
                src={ATHENA_IMAGE_SRC}
                alt=""
                fill
                className="object-cover object-top"
                sizes="112px"
              />
            </div>
            <p className="font-landing-body mt-3 text-sm font-semibold text-neutral-800">
              Patient
            </p>
            <p className="font-landing-body mt-1 text-center text-xs text-neutral-500">
              AI patient speaking
            </p>
          </div>

          <div className="relative flex min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-sm sm:rounded-2xl">
            <div className="showcase-transcript-header shrink-0 border-b border-slate-100 sm:px-5 sm:py-3">
              <p className="showcase-eyebrow font-landing-body font-semibold uppercase tracking-[0.12em] text-neutral-500 sm:text-xs">
                Live transcript
              </p>
            </div>
            <div className="relative min-h-0 flex-1 overflow-hidden">
              <div className="landing-transcript-scroll showcase-stack flex flex-col px-2 py-2 sm:space-y-4 sm:px-5 sm:py-4 lg:px-6 lg:py-5">
                {[...TRANSCRIPT_LINES, ...TRANSCRIPT_LINES].map((line, index) => (
                  <TranscriptBubble
                    key={`${line.role}-${index}`}
                    role={line.role}
                    text={line.text}
                  />
                ))}
              </div>
              <div className="pointer-events-none absolute inset-x-0 top-0 h-6 bg-gradient-to-b from-white to-transparent sm:h-10" />
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-6 bg-gradient-to-b from-transparent to-white sm:h-10" />
            </div>
          </div>

          <div className="hidden flex-col items-center justify-center rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-sm lg:flex">
            <div className="relative h-24 w-24 overflow-hidden rounded-full border-4 border-white shadow-md xl:h-28 xl:w-28">
              <Image
                src="/images/landing/hero-doctor.png"
                alt=""
                fill
                className="object-cover object-top"
                sizes="112px"
              />
            </div>
            <p className="font-landing-body mt-3 text-sm font-semibold text-neutral-800">
              You
            </p>
            <p className="font-landing-body mt-1 text-center text-xs text-neutral-500">
              Clinician speaking
            </p>
          </div>
        </div>
      </ShowcaseSceneBody>

      <div className="landing-showcase-scene-header mt-2 flex shrink-0 justify-center sm:mt-6">
        <div className="showcase-voice-wrap bg-osce-accent shadow-[0_8px_24px_rgba(37,99,235,0.25)] sm:rounded-xl sm:px-8 sm:py-3.5">
          <VoiceMemoBars
            size="compact"
            barClassName="voice-memo-bar rounded-full bg-white/95 sm:w-1"
            gapClassName="gap-[2px] sm:gap-1"
            heightClassName="showcase-voice-bars sm:h-8"
          />
        </div>
      </div>
    </ShowcaseScene>
  );
}

type MarketplaceBookingSceneProps = {
  sessionTitle: string;
};

function MarketplaceBookingScene({ sessionTitle }: MarketplaceBookingSceneProps) {
  return (
    <ShowcaseScene className="bg-gradient-to-br from-slate-50 to-osce-accent-muted/30 sm:p-8 lg:p-10">
      <ShowcaseSceneHeader className="mb-2 sm:mb-6">
        <p className="showcase-title font-landing-heading font-semibold text-neutral-900 sm:text-2xl">
          Book a practice session
        </p>
        <p className="showcase-subtitle font-landing-body mt-1 hidden text-neutral-600 sm:mt-2 sm:block sm:text-base">
          Pick a date and match with a colleague on the marketplace.
        </p>
      </ShowcaseSceneHeader>

      <ShowcaseSceneBody>
        <div className="showcase-stack flex h-full min-h-0 w-full flex-col gap-2 sm:grid sm:grid-cols-[1.2fr_1fr] sm:gap-5 lg:gap-6">
          <div className="flex min-h-0 w-full flex-1 flex-col sm:showcase-card sm:rounded-2xl sm:bg-osce-accent-muted/35 sm:p-6">
            <div className="mb-1 flex w-full shrink-0 items-center justify-between sm:mb-4">
              <p className="showcase-body font-landing-body font-semibold text-neutral-800 sm:text-lg">
                March 2026
              </p>
              <span className="showcase-eyebrow font-landing-body hidden rounded-full bg-white px-2 py-0.5 font-medium text-osce-accent shadow-sm sm:inline sm:px-3 sm:py-1 sm:text-xs">
                Selecting date
              </span>
            </div>
            <div className="mb-1 grid w-full shrink-0 grid-cols-7 gap-1 sm:mb-3 sm:gap-2">
              {CALENDAR_DAYS.map((day, index) => (
                <span
                  key={`${day}-${index}`}
                  className="showcase-calendar-day font-landing-body text-center font-medium text-neutral-500 sm:text-xs"
                >
                  {day}
                </span>
              ))}
            </div>
            <div className="grid w-full min-h-0 flex-1 grid-cols-7 grid-rows-4 gap-1 sm:gap-2">
              {CALENDAR_CELLS.map((day) => {
                const isSelected = day === 14;
                const isHovered = day === 15;
                return (
                  <button
                    key={day}
                    type="button"
                    className={`showcase-calendar-cell font-landing-body flex items-center justify-center transition-colors sm:min-h-[2.75rem] sm:rounded-lg sm:text-base ${
                      isSelected
                        ? "bg-osce-accent font-semibold text-white shadow-sm"
                        : isHovered
                          ? "bg-white text-osce-accent"
                          : "text-neutral-700 hover:bg-white/70"
                    }`}
                  >
                    {day}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="showcase-stack flex w-full shrink-0 flex-col gap-1.5 sm:min-h-0 sm:flex-1 sm:gap-5">
            <div className="showcase-card hidden min-h-0 flex-1 flex-col border border-slate-200/70 bg-slate-50/80 sm:flex sm:rounded-2xl sm:p-6">
              <p className="showcase-eyebrow font-landing-body font-semibold uppercase tracking-[0.12em] text-neutral-500 sm:text-xs">
                Session details
              </p>
              <p className="showcase-title mt-1 font-landing-heading font-semibold leading-snug text-neutral-900 sm:mt-3 sm:text-xl">
                {sessionTitle}
              </p>
              <p className="showcase-body font-landing-body mt-0.5 text-neutral-600 sm:mt-3 sm:text-base">
                Thu 14 Mar · 7:00 pm
              </p>
              <p className="showcase-body font-landing-body mt-0.5 text-neutral-600 sm:mt-2 sm:text-base">
                20 min · Video session
              </p>
            </div>

            <div className="w-full shrink-0 rounded-lg border border-emerald-200/80 bg-emerald-50/90 py-2 sm:showcase-card sm:rounded-2xl sm:p-6">
              <div className="flex items-center gap-1.5 sm:items-start sm:gap-4">
                <span className="showcase-icon-badge flex shrink-0 items-center justify-center rounded-full bg-emerald-600 text-white sm:h-11 sm:w-11">
                  <HiOutlineCheck aria-hidden />
                </span>
                <div className="min-w-0">
                  <p className="showcase-body font-landing-heading font-semibold leading-snug text-emerald-900 sm:text-lg">
                    Session confirmed
                  </p>
                  <p className="showcase-body font-landing-body mt-0.5 hidden leading-snug text-emerald-800 sm:mt-2 sm:block sm:text-base">
                    Your colleague will join at the scheduled time.
                  </p>
                  <p className="showcase-body font-landing-body mt-0.5 leading-snug text-emerald-800 sm:hidden">
                    {sessionTitle} · Thu 14 Mar, 7:00 pm
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </ShowcaseSceneBody>
    </ShowcaseScene>
  );
}

function InstitutionTrainingScene() {
  const tiles = [
    {
      label: "AI patient",
      sublabel: "Chest pain case",
      image: ATHENA_IMAGE_SRC,
      active: false,
    },
    {
      label: "Supervisor",
      sublabel: "Observing circuit",
      initials: "SV",
      active: false,
    },
    {
      label: "Trainee",
      sublabel: "Consulting now",
      initials: "JT",
      active: true,
    },
    {
      label: "Trainee",
      sublabel: "Listening in",
      initials: "AM",
      active: false,
    },
  ];

  return (
    <ShowcaseScene className="bg-gradient-to-br from-slate-50 to-osce-accent-muted/30 sm:p-5 lg:p-8">
      <ShowcaseSceneHeader className="mb-2 flex items-start justify-between gap-2 sm:mb-3">
        <div className="min-w-0">
          <p className="showcase-title font-landing-heading font-semibold text-neutral-900 sm:text-lg">
            Institution training room
          </p>
          <p className="showcase-subtitle font-landing-body mt-0.5 hidden leading-snug text-neutral-600 sm:mt-1 sm:block sm:text-sm">
            Trainee leads the AI case while peers and a supervisor observe.
          </p>
        </div>
        <span className="showcase-eyebrow font-landing-body shrink-0 rounded-full bg-osce-accent px-2 py-0.5 font-semibold text-white sm:px-2.5 sm:text-xs">
          Live
        </span>
      </ShowcaseSceneHeader>

      <ShowcaseSceneBody>
        <div className="grid h-full min-h-0 grid-cols-2 gap-1.5 sm:gap-3">
          {tiles.map((tile, index) => (
            <div
              key={`${tile.label}-${index}`}
              className={`showcase-card flex min-h-0 flex-col border bg-white shadow-sm sm:rounded-2xl sm:p-3 ${
                tile.active
                  ? "border-osce-accent ring-2 ring-osce-accent/20"
                  : "border-slate-200/80"
              }`}
            >
              {tile.active ? (
                <span className="showcase-eyebrow font-landing-body mb-0.5 self-center rounded-full bg-osce-accent px-1.5 py-0.5 font-semibold text-white sm:mb-2 sm:px-2 sm:text-[10px]">
                  Speaking
                </span>
              ) : (
                <span className="mb-0.5 block h-2 sm:mb-2 sm:h-[18px]" aria-hidden />
              )}
              <div className="showcase-tile-avatar relative mx-auto mb-1 flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-slate-100 sm:mb-2 sm:h-14 sm:w-14">
                {tile.image ? (
                  <Image
                    src={tile.image}
                    alt=""
                    fill
                    className="object-cover object-top"
                    sizes="56px"
                  />
                ) : (
                  <span className="showcase-body font-landing-body font-semibold text-neutral-600 sm:text-sm">
                    {tile.initials}
                  </span>
                )}
              </div>
              <p className="showcase-body font-landing-heading text-center font-semibold leading-snug text-neutral-900 sm:text-sm">
                {tile.label}
              </p>
              <p className="showcase-eyebrow font-landing-body mt-0.5 text-center leading-snug text-neutral-500 sm:mt-1 sm:text-xs">
                {tile.sublabel}
              </p>
            </div>
          ))}
        </div>
      </ShowcaseSceneBody>

      <div className="landing-showcase-scene-header showcase-footer-bar mt-2 flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-200/80 bg-white/90 sm:mt-3 sm:gap-2 sm:rounded-xl sm:px-3 sm:py-2">
        <LuStethoscope className="h-3 w-3 shrink-0 text-osce-accent sm:h-4 sm:w-4" aria-hidden />
        <p className="showcase-body font-landing-body leading-snug text-neutral-600 sm:text-xs">
          Trainee consulting AI patient · Supervisor and peer observing
        </p>
      </div>
    </ShowcaseScene>
  );
}

const ACCENT_ROTATE = [3, -2, 4] as const;

export type LandingFeaturesShowcaseProps = {
  /** Marketplace slide session title (base landing uses SCA). */
  sessionTitle?: string;
};

export function LandingFeaturesShowcase({
  sessionTitle = "SCA practise session",
}: LandingFeaturesShowcaseProps = {}) {
  const [activeIndex, setActiveIndex] = useState(0);
  // Resolved once. The index is only ever set from this list, so the fallback
  // is unreachable — it is here so the three reads below need no guard each.
  const activeSlide = SHOWCASE_SLIDES[activeIndex] ?? SHOWCASE_SLIDES[0];

  useEffect(() => {
    const timer = setInterval(
      () => setActiveIndex((current) => (current + 1) % SHOWCASE_SLIDES.length),
      7000,
    );
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="relative mt-12 w-full sm:mt-16 lg:mx-auto lg:max-w-6xl">
      <motion.div
        className="absolute inset-0 rounded-2xl bg-gradient-to-r from-osce-accent to-osce-accent-hover opacity-20 sm:rounded-3xl"
        animate={{ rotate: ACCENT_ROTATE[activeIndex] }}
        transition={{ duration: 0.55, ease: [0.4, 0, 0.2, 1] }}
      />
      <div className="relative overflow-hidden rounded-xl border border-slate-300 bg-white shadow-xl sm:rounded-3xl">
        <div
          className={`${SHOWCASE_VIEWPORT_CLASS} [perspective:1200px]`}
          aria-live="polite"
          aria-label={`Product showcase: ${activeSlide.label}`}
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={activeSlide.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.45, ease: [0.4, 0, 0.2, 1] }}
              className="absolute inset-0 overflow-hidden bg-white lg:[transform-style:preserve-3d]"
            >
              {activeIndex === 0 && <VoiceConsultationScene />}
              {activeIndex === 1 && (
                <MarketplaceBookingScene sessionTitle={sessionTitle} />
              )}
              {activeIndex === 2 && <InstitutionTrainingScene />}
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-slate-100 bg-white px-3 py-2.5 sm:px-5 sm:py-3">
          <p className="landing-showcase-chrome-label min-w-0 truncate font-landing-body font-medium text-neutral-700 sm:text-sm">
            {activeSlide.label}
          </p>
          <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
            {SHOWCASE_SLIDES.map((slide, index) => (
              <button
                key={slide.id}
                type="button"
                aria-label={`Show ${slide.label}`}
                onClick={() => setActiveIndex(index)}
                className={`h-1.5 rounded-full transition-all sm:h-2 ${
                  index === activeIndex
                    ? "w-5 bg-osce-accent sm:w-6"
                    : "w-1.5 bg-slate-300 hover:bg-slate-400 sm:w-2"
                }`}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
