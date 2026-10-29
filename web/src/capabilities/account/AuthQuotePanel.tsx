"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { ATHENA_IMAGE_SRC, Eyebrow } from "@/foundation/ui";
import { MARQUEE_TESTIMONIALS } from "@/foundation/ui/marqueeTestimonials";
import { cn } from "@/foundation/ui/cn";

const WAVE_BARS = Array.from({ length: 28 }, (_, index) => index);

/** A sample of what a station's feedback looks like; not the reader's data. */
const SAMPLE_DOMAINS = [
  { label: "Data gathering", percent: 78, weak: false },
  { label: "Clinical management", percent: 64, weak: false },
  { label: "Relating to others", percent: 52, weak: true },
] as const;

/**
 * The navy panel beside the sign-in card: Athena, a sample of the feedback, and
 * the live "What our users say" quote. Hidden at 960px and below, where the card
 * is the whole page.
 */
export default function AuthQuotePanel() {
  /*
   * Starts at the first one, then moves to a random one once mounted.
   *
   * Picking randomly in the initial state made the server render one quote and
   * the browser another, so React discarded the whole tree and re-rendered the
   * sign-in page on every visit. The variety is worth having; paying for it
   * with a hydration mismatch is not.
   */
  const [testimonialIndex, setTestimonialIndex] = useState(0);
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    setTestimonialIndex(Math.floor(Math.random() * MARQUEE_TESTIMONIALS.length));
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setIsVisible(false);
      window.setTimeout(() => {
        setTestimonialIndex((prev) => (prev + 1) % MARQUEE_TESTIMONIALS.length);
        setIsVisible(true);
      }, 300);
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  // The modulo keeps the index in range; the fallback is what says so.
  const testimonial = MARQUEE_TESTIMONIALS[testimonialIndex] ?? MARQUEE_TESTIMONIALS[0];
  if (!testimonial) return null;

  return (
    <aside className="hidden min-w-0 flex-col gap-6 overflow-hidden rounded-[22px] bg-site-navy p-9 text-white min-[961px]:flex">
      <div className="flex items-center gap-3" aria-hidden="true">
        <Image
          src={ATHENA_IMAGE_SRC}
          alt=""
          width={48}
          height={48}
          className="h-12 w-12 rounded-full border border-white/20 object-cover"
        />
        <div className="flex flex-col">
          <b className="font-landing-heading text-base">Athena</b>
          <span className="text-sm text-site-on-navy">Ready for your next station</span>
        </div>
      </div>

      <div className="flex h-14 items-center gap-1" aria-hidden="true">
        {WAVE_BARS.map((bar) => (
          <i
            key={bar}
            className="site-wave-bar h-full min-w-0 flex-1 rounded-full bg-site-on-navy"
            style={{ animationDelay: `${(bar % 9) * 0.11}s` }}
          />
        ))}
      </div>

      <div className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/[0.07] p-5" aria-hidden="true">
        <Eyebrow onNavy>Sample feedback · Chest pain</Eyebrow>
        {SAMPLE_DOMAINS.map((domain) => (
          <div key={domain.label} className="grid grid-cols-[1fr_120px] items-center gap-3 text-sm text-site-on-navy">
            <span>{domain.label}</span>
            <span className="h-2 overflow-hidden rounded-full bg-white/15">
              <i
                className={cn("block h-full rounded-full", domain.weak ? "bg-site-amber" : "bg-site-on-navy")}
                style={{ width: `${domain.percent}%` }}
              />
            </span>
          </div>
        ))}
      </div>

      <div className="mt-auto flex flex-col gap-3">
        <Eyebrow onNavy>What our users say</Eyebrow>
        <figure className={cn("transition-opacity duration-300 motion-reduce:transition-none", isVisible ? "opacity-100" : "opacity-0")}>
          <blockquote className="text-[15px] leading-relaxed text-white">{testimonial.excerpt}</blockquote>
          <figcaption className="mt-3 text-sm text-site-on-navy">
            <b className="font-semibold text-white">{testimonial.name}</b>, {testimonial.role}
          </figcaption>
        </figure>
        <div className="flex items-center gap-1.5" aria-hidden="true">
          {MARQUEE_TESTIMONIALS.map((item, index) => (
            <span
              key={item.name}
              className={cn(
                "h-1.5 rounded-full transition-all duration-300 motion-reduce:transition-none",
                index === testimonialIndex ? "w-4 bg-white" : "w-1.5 bg-white/30",
              )}
            />
          ))}
        </div>
      </div>
    </aside>
  );
}
