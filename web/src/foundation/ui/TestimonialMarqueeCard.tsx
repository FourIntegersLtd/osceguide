"use client";

import { LuQuote } from "react-icons/lu";
import type { ReactNode } from "react";
import type { MarqueeTestimonial } from "@/foundation/ui/marqueeTestimonials";
import { cn } from "@/foundation/ui";

const MENTION = "@OSCEGuide";

function getInitials(name: string): string {
  const withoutTitle = name.replace(/^Dr\.?\s+/i, "").trim();
  const parts = withoutTitle.split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0];
  const last = parts[parts.length - 1]?.[0];
  if (parts.length >= 2 && first && last) {
    return (first + last).toUpperCase();
  }
  const letters = withoutTitle.replace(/[^A-Za-z]/g, "");
  return (letters.slice(0, 2) || withoutTitle.slice(0, 2)).toUpperCase();
}

function splitKeep(
  haystack: string,
  needle: string,
): Array<{ value: string; kind: "text" | "highlight" }> {
  const result: Array<{ value: string; kind: "text" | "highlight" }> = [];
  let remaining = haystack;
  while (remaining.length > 0) {
    const idx = remaining.indexOf(needle);
    if (idx === -1) {
      result.push({ value: remaining, kind: "text" });
      break;
    }
    if (idx > 0) {
      result.push({ value: remaining.slice(0, idx), kind: "text" });
    }
    result.push({ value: needle, kind: "highlight" });
    remaining = remaining.slice(idx + needle.length);
  }
  return result;
}

function renderMentionedText(text: string, keyPrefix: string): ReactNode[] {
  return text.split(/(@OSCEGuide)/g).flatMap((bit, index) => {
    if (!bit) {
      return [];
    }
    if (bit === MENTION) {
      return [
        <span
          key={`${keyPrefix}-m-${index}`}
          className="font-medium text-osce-accent"
        >
          {bit}
        </span>,
      ];
    }
    return [<span key={`${keyPrefix}-t-${index}`}>{bit}</span>];
  });
}

function renderExcerpt(excerpt: string, highlight: string): ReactNode {
  const segments =
    highlight && excerpt.includes(highlight)
      ? splitKeep(excerpt, highlight)
      : [{ value: excerpt, kind: "text" as const }];

  return segments.map((segment, index) => {
    if (segment.kind === "highlight") {
      return (
        <mark
          key={`h-${index}`}
          className="rounded-sm bg-osce-accent-muted px-0.5 text-inherit"
        >
          {segment.value}
        </mark>
      );
    }
    return renderMentionedText(segment.value, `s-${index}`);
  });
}

type TestimonialMarqueeCardProps = {
  testimonial: MarqueeTestimonial;
  layout?: "marquee" | "inline";
  /**
   * The landing's body-text class for this variant.
   *
   * A prop, not a context read. The card used to reach into the landing's
   * variant provider for one class name, with a fallback for when there was
   * none — which is most of the time, because the sign-in page shows these too.
   * Passing it keeps the card usable anywhere.
   */
  bodyClassName?: string;
  className?: string;
};

/** The landing's own body-text treatment, which is also the right default. */
const DEFAULT_BODY_CLASS =
  "font-landing-body text-sm leading-relaxed text-b2c-text-secondary sm:text-[14.5px] sm:leading-[1.6]";

export function TestimonialMarqueeCard({
  testimonial,
  layout = "marquee",
  bodyClassName,
  className,
}: TestimonialMarqueeCardProps) {
  const initials = getInitials(testimonial.name);
  const isInline = layout === "inline";

  return (
    <article
      className={cn(
        "flex flex-col rounded-landing-card border border-landing-warm bg-[color:var(--landing-card,#FCFCFD)] shadow-landing-soft",
        isInline
          ? "w-full p-6"
          : "h-[280px] w-[min(300px,calc(100vw-3rem))] shrink-0 p-5 sm:h-[300px] sm:w-[320px] sm:p-6",
        className,
      )}
    >
      <header className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-landing-warm bg-[color:var(--landing-card-muted,#ffffff)] font-landing-body text-sm font-semibold text-[color:var(--landing-ink-body,#334155)]"
            aria-hidden
          >
            {initials}
          </span>
          <div className="min-w-0">
            <p
              className={cn(
                "font-landing-body text-[15px] font-semibold leading-tight text-osce-ink-900",
                !isInline && "truncate",
              )}
            >
              {testimonial.name}
            </p>
            <p
              className={cn(
                "font-landing-body text-sm text-b2c-text-secondary",
                !isInline && "truncate",
              )}
            >
              {testimonial.role}
            </p>
          </div>
        </div>
        <span
          className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-osce-lg bg-osce-accent text-white"
          aria-hidden
        >
          <LuQuote className="h-3.5 w-3.5" />
        </span>
      </header>
      <p
        className={cn(
          "mt-5",
          !isInline && "flex-1",
          bodyClassName ?? DEFAULT_BODY_CLASS,
        )}
      >
        {renderExcerpt(testimonial.excerpt, testimonial.highlight)}
      </p>
    </article>
  );
}
