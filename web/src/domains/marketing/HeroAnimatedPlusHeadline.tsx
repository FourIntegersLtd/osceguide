"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

export const HERO_PLUS_HEADLINE_WORDS = [
  "Practice",
  "Simulation",
  "Debrief",
  "Tutoring",
] as const;

type HeroAnimatedPlusHeadlineProps = {
  words?: readonly string[];
  intervalMs?: number;
  className?: string;
};

export function HeroAnimatedPlusHeadline({
  words = HERO_PLUS_HEADLINE_WORDS,
  intervalMs = 2600,
  className = "",
}: HeroAnimatedPlusHeadlineProps) {
  const [wordIndex, setWordIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(
      () => setWordIndex((current) => (current + 1) % words.length),
      intervalMs,
    );
    return () => clearInterval(timer);
  }, [intervalMs, words.length]);

  const word = words[wordIndex];

  return (
    <h1
      className={`font-landing-heading text-[clamp(2.875rem,8.5vw,6.125rem)] font-normal leading-[1.12] tracking-[-0.02em] text-neutral-900 ${className}`}
    >
      <span className="inline-flex max-w-full flex-nowrap items-baseline whitespace-nowrap">
        <span className="mr-[9px] sm:mr-[11px]">AI</span>
        <span className="inline-flex items-baseline whitespace-nowrap">
          <span className="relative inline-block overflow-hidden align-bottom">
            <AnimatePresence mode="wait">
              <motion.span
                key={word}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.5, ease: "easeInOut" }}
                className="inline-block whitespace-nowrap pb-0.5"
              >
                {word}
              </motion.span>
            </AnimatePresence>
          </span>
          <span className="ml-[2px] text-osce-accent">+</span>
        </span>
      </span>
    </h1>
  );
}
