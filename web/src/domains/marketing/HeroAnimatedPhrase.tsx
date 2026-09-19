"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

export type HeroAnimatedPhraseItem = {
  prefix: string;
  word: string;
};

export const MAIN_HERO_PHRASES: HeroAnimatedPhraseItem[] = [
  { prefix: "is never ", word: "tired" },
  { prefix: "is never ", word: "busy" },
  { prefix: "is never ", word: "unavailable" },
  { prefix: "is never ", word: "late" },
  { prefix: "is never ", word: "distracted" },
  { prefix: "never ", word: "cancels" },
  { prefix: "never ", word: "reschedules" },
];

type HeroAnimatedPhraseProps = {
  phrases?: HeroAnimatedPhraseItem[];
  intervalMs?: number;
  /** Solid Tailwind blue — original base landing hero accent. */
  variant?: "default" | "base";
};

export function HeroAnimatedPhrase({
  phrases = MAIN_HERO_PHRASES,
  intervalMs = 2200,
  variant = "default",
}: HeroAnimatedPhraseProps) {
  const [phraseIndex, setPhraseIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(
      () => setPhraseIndex((current) => (current + 1) % phrases.length),
      intervalMs,
    );
    return () => clearInterval(timer);
  }, [intervalMs, phrases.length]);

  const phrase = phrases[phraseIndex];

  return (
    <span className="relative inline-block overflow-hidden align-bottom">
      <AnimatePresence mode="wait">
        <motion.span
          key={`${phrase.prefix}${phrase.word}`}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.5, ease: "easeInOut" }}
          className={
            variant === "base"
              ? "inline-block whitespace-nowrap text-osce-accent"
              : "inline-block whitespace-nowrap bg-gradient-to-r from-osce-accent to-osce-accent-hover bg-clip-text text-transparent"
          }
        >
          {phrase.prefix}
          {phrase.word}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}
