"use client";

import { HiOutlineStar, HiStar } from "react-icons/hi2";
import { useState } from "react";
import { cn } from "@/foundation/ui";
import type { TestimonialPermission } from "@/capabilities/help/productFeedbackModel";
import { TESTIMONIAL_OPTIONS } from "@/capabilities/help/productFeedbackModel";

/*
 * The two field widgets of `ProductFeedbackForm` — the stars and the
 * testimonial question — split out so the form file stays readable. Same
 * markup and behaviour as the retiring client's; only the hover state moved
 * inside the star row, which is where it was only ever used.
 */

const STAR_LABELS = ["Poor", "Fair", "Okay", "Good", "Excellent"] as const;

export function StarRating({
  value,
  onChange,
  compact,
}: {
  value: number;
  onChange: (value: number) => void;
  compact: boolean;
}) {
  const [hoverRating, setHoverRating] = useState(0);
  const activeRating = hoverRating || value;

  return (
    <div
      className={cn(
        "flex items-center gap-1",
        compact ? "justify-start" : "justify-center gap-1.5",
      )}
      role="radiogroup"
      aria-label="Experience rating"
    >
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = star <= activeRating;
        return (
          <button
            key={star}
            type="button"
            role="radio"
            aria-checked={value === star}
            aria-label={`${star}. ${STAR_LABELS[star - 1]}`}
            className={cn(
              "rounded-md p-1 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent/30",
              filled ? "text-osce-ink-900" : "text-osce-ink-400 hover:text-osce-ink-900",
            )}
            onMouseEnter={() => setHoverRating(star)}
            onMouseLeave={() => setHoverRating(0)}
            onClick={() => onChange(star)}
          >
            {filled ? (
              <HiStar className={compact ? "h-5 w-5" : "h-6 w-6"} aria-hidden />
            ) : (
              <HiOutlineStar className={compact ? "h-5 w-5" : "h-6 w-6"} aria-hidden />
            )}
          </button>
        );
      })}
    </div>
  );
}

export function TestimonialChoice({
  idPrefix,
  value,
  onChange,
  compact,
}: {
  idPrefix: string;
  value: TestimonialPermission | "";
  onChange: (value: TestimonialPermission) => void;
  compact: boolean;
}) {
  return (
    <fieldset className={compact ? undefined : "space-y-1.5"}>
      <legend className="text-osce-meta text-b2c-text-muted">
        {compact ? (
          <>
            Use as testimonial? <span className="text-osce-danger">*</span>
          </>
        ) : (
          <>
            May we feature it as a testimonial? <span className="text-osce-danger">*</span>
          </>
        )}
      </legend>
      <div
        className={cn(
          compact ? "mt-2 flex flex-wrap gap-x-4 gap-y-2" : "grid gap-2 sm:grid-cols-3",
        )}
      >
        {TESTIMONIAL_OPTIONS.map((option) => (
          <label
            key={option.value}
            className={cn(
              "flex cursor-pointer items-center gap-2.5 text-osce-body text-osce-ink-900",
              !compact &&
                "rounded-control border px-3 py-2.5 transition-colors has-[:checked]:border-osce-ink-900 has-[:checked]:ring-1 has-[:checked]:ring-osce-ink-900",
              !compact && (value === option.value ? "border-osce-ink-900" : "border-osce-border hover:border-osce-ink-400"),
            )}
          >
            <input
              type="radio"
              name={`${idPrefix}-testimonial`}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              className="h-4 w-4 shrink-0 border-b2c-border text-osce-accent focus:ring-osce-accent/30"
              required
            />
            {compact ? option.compactLabel : option.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
