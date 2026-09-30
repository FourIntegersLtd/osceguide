"use client";

import { useEffect, useState } from "react";
import { MARQUEE_TESTIMONIALS } from "@/foundation/ui/marqueeTestimonials";
import { TestimonialMarqueeCard } from "@/foundation/ui/TestimonialMarqueeCard";
import { cn } from "@/foundation/ui/cn";
import { authEyebrow, authQuoteBody } from "@/foundation/ui/authTheme";

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
    <div className="hidden min-h-0 flex-col justify-center px-6 lg:flex lg:px-8 xl:px-12">
      <div className="w-full max-w-md" aria-live="polite">
        <p className={authEyebrow}>What our users say</p>
        <div
          className={cn(
            "mt-5 transition-opacity duration-300",
            isVisible ? "opacity-100" : "opacity-0",
          )}
        >
          <TestimonialMarqueeCard
            layout="inline"
            testimonial={testimonial}
            bodyClassName={authQuoteBody}
          />
        </div>
        <div
          className="mt-5 flex items-center justify-center gap-1.5"
          aria-hidden
        >
          {MARQUEE_TESTIMONIALS.map((item, index) => (
            <span
              key={item.name}
              className={cn(
                "h-1.5 rounded-full transition-all duration-300",
                index === testimonialIndex
                  ? "w-4 bg-osce-accent"
                  : "w-1.5 bg-border",
              )}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
