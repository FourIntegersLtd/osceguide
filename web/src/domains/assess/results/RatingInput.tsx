"use client";

import { cn, b2bTokens } from "@/foundation/ui";
import { boardSeg, boardSegChoice } from "@/foundation/ui/boardKit";
import { ratingLabel, type Rating, type RatingValue } from "@/capabilities/feedback/rubric";
import { ratingChoices, ratingVariant } from "@/domains/assess/results/reviewForm";

/**
 * One rating, entered the way the rubric's rating kind asks for it.
 *
 * A scale (G / A / R, or an author's own words) and met / not met are a row
 * of buttons; a short whole-number range is a row of numbers; anything longer
 * or decimal is a number field bounded by the rubric's minimum and maximum.
 * The kind comes from `ReviewFormRead.rating`, so the same control serves
 * every exam. The backend validates the value again on save (`invalid_rating`).
 */
export function RatingInput({
  rating,
  label,
  value,
  disabled,
  onChange,
}: {
  rating: Rating;
  /** Read out by assistive technology for the whole row. */
  label: string;
  value: RatingValue | null;
  disabled?: boolean;
  onChange: (value: RatingValue) => void;
}) {
  const choices = ratingChoices(rating);

  if (choices === null) {
    return (
      <input
        type="number"
        aria-label={label}
        disabled={disabled}
        min={rating.minimum ?? undefined}
        max={rating.maximum ?? undefined}
        step={rating.step === "integer" ? 1 : "any"}
        value={typeof value === "number" ? value : ""}
        onChange={(event) => {
          const parsed = Number(event.target.value);
          if (event.target.value !== "" && Number.isFinite(parsed)) onChange(parsed);
        }}
        placeholder={rating.maximum !== null && rating.maximum !== undefined ? `out of ${rating.maximum}` : undefined}
        className={cn(b2bTokens.b2bInputBase, "w-32")}
      />
    );
  }

  return (
    <div className={boardSeg} role="group" aria-label={label}>
      {choices.map((choice) => {
        const selected = value === choice;
        return (
          <button
            key={String(choice)}
            type="button"
            disabled={disabled}
            aria-pressed={selected}
            onClick={() => onChange(choice)}
            className={boardSegChoice(selected, ratingVariant(rating, choice))}
          >
            {/* A range value reads as the bare number on a button; "3/4" is for summaries. */}
            {typeof choice === "number" ? choice : ratingLabel(rating, choice)}
          </button>
        );
      })}
    </div>
  );
}
