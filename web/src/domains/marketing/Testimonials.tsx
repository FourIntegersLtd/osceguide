"use client";

import {
  MARQUEE_TESTIMONIALS,
  type MarqueeTestimonial,
} from "@/domains/marketing/support/testimonials";
import Link from "next/link";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";
import { TestimonialMarqueeCard } from "@/foundation/ui/TestimonialMarqueeCard";
import { LOGIN_PATH } from "@/foundation/attribution/partnerConstants";

type TestimonialCta = {
  label: string;
  href: string;
};

type TestimonialsProps = {
  items?: MarqueeTestimonial[];
  className?: string;
  titleBefore?: string;
  titleHighlight?: string;
  titleAfter?: string;
  /** Pass null to render no subtitle at all; omit it for the default copy. */
  description?: string | null;
  primaryCta?: TestimonialCta;
  secondaryCta?: TestimonialCta;
};

function MarqueeSet({
  items,
  duplicate = false,
}: {
  items: MarqueeTestimonial[];
  duplicate?: boolean;
}) {
  return (
    <ul
      className={`flex gap-5 pe-5 ${duplicate ? "testimonial-marquee-duplicate" : ""}`}
      aria-hidden={duplicate || undefined}
    >
      {items.map((item) => (
        <li key={`${duplicate ? "dup-" : ""}${item.name}`}>
          <TestimonialMarqueeCard testimonial={item} />
        </li>
      ))}
    </ul>
  );
}

function Testimonials({
  items = MARQUEE_TESTIMONIALS,
  className = "",
  titleBefore = "What Our ",
  titleHighlight = "Users",
  titleAfter = " Say",
  description =
    "Doctors use OSCE Guide to practise voice-first consultations, get structured feedback, and walk into exam day ready.",
  primaryCta = { label: "Start practising", href: LOGIN_PATH },
  secondaryCta = {
    label: "Book a demo",
    href: "mailto:hello@fourintegers.com?subject=OSCE%20Guide%20Demo",
  },
}: TestimonialsProps) {
  const { type } = useLandingVariant();

  return (
    <section
      id="testimonials"
      aria-labelledby="testimonials-heading"
      className={`scroll-mt-20 overflow-hidden py-16 sm:py-20 ${landingSectionSurfaces.testimonials} ${className}`}
    >
      <div className={`${type.sectionShell} mb-10 sm:mb-12`}>
        <div className="mx-auto max-w-3xl text-center">
          <h2 id="testimonials-heading" className={type.sectionTitle}>
            {titleBefore}
            <span className="text-osce-accent">{titleHighlight}</span>
            {titleAfter}
          </h2>
          {description && (
            <p className={type.sectionSubtitleCentered}>{description}</p>
          )}
          <div className="mt-8 flex flex-col items-stretch justify-center gap-4 sm:flex-row sm:items-center">
            <Link href={primaryCta.href} className={`${type.ctaInk} w-full sm:w-auto`}>
              {primaryCta.label}
            </Link>
            <Link href={secondaryCta.href} className={`${type.ctaSecondary} w-full sm:w-auto`}>
              {secondaryCta.label}
            </Link>
          </div>
        </div>
      </div>

      <div
        className="testimonial-marquee-viewport focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-b2c-primary-subtle"
        tabIndex={0}
        aria-label="Scrolling testimonials. Focus or hover to pause."
      >
        <div className="testimonial-marquee-track flex">
          <MarqueeSet items={items} />
          <MarqueeSet items={items} duplicate />
        </div>
      </div>
    </section>
  );
}

export default Testimonials;
