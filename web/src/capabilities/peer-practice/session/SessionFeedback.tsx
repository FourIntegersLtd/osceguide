"use client";

import { useState, type FormEvent } from "react";
import { HiOutlineStar } from "react-icons/hi2";
import { Button, productTokens } from "@/foundation/ui";
import { submitPracticeFeedback } from "../api";
import { failureText } from "../support/failure";
import { b2cCard } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";

const RATING_LABELS: Record<number, string> = { 5: "Excellent", 4: "Very Good", 3: "Good", 2: "Fair", 1: "Poor" };

/**
 * The rating one candidate gives the other. "Would you practise again" is
 * required, the stars and the comment are not, and Skip leaves without
 * sending anything — as the retiring form did.
 */
export function SessionFeedback({ sessionId, onDone }: { sessionId: string; onDone: () => void }) {
  const [wouldPracticeAgain, setWouldPracticeAgain] = useState<boolean | null>(null);
  const [experienceRating, setExperienceRating] = useState<number | null>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (wouldPracticeAgain === null) {
      setError("Please indicate if you would practice with this user again");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await submitPracticeFeedback(sessionId, {
        would_practice_again: wouldPracticeAgain,
        rating: experienceRating,
        comment: feedbackText || null,
      });
      onDone();
    } catch (cause) {
      setError(failureText(cause, "Failed to submit feedback. Please try again."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className={cn(b2cCard, "p-5 text-left")}>
      <div className="mb-5">
        <h3 className="text-osce-subheading font-semibold text-osce-ink-900">Colleague practice feedback</h3>
        <p className="mt-0.5 text-osce-meta text-b2c-text-muted">
          Your answers help us match you with better practice partners.
        </p>
      </div>
      <form onSubmit={(event) => void submit(event)} className="space-y-5">
        <div>
          <p className="mb-1.5 text-osce-meta text-b2c-text-muted">
            Would you practise with this colleague again? <span className="text-osce-danger-text">*</span>
          </p>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              aria-pressed={wouldPracticeAgain === true}
              onClick={() => setWouldPracticeAgain(true)}
              className={`rounded-control border px-3 py-2.5 text-osce-body font-medium transition-colors ${wouldPracticeAgain === true ? "border-osce-ink-900 bg-osce-surface text-osce-ink-900 ring-1 ring-osce-ink-900" : "border-osce-border text-b2c-text-muted hover:border-osce-ink-400"}`}
            >
              Yes
            </button>
            <button
              type="button"
              aria-pressed={wouldPracticeAgain === false}
              onClick={() => setWouldPracticeAgain(false)}
              className={`rounded-control border px-3 py-2.5 text-osce-body font-medium transition-colors ${wouldPracticeAgain === false ? "border-osce-ink-900 bg-osce-surface text-osce-ink-900 ring-1 ring-osce-ink-900" : "border-osce-border text-b2c-text-muted hover:border-osce-ink-400"}`}
            >
              No
            </button>
          </div>
        </div>

        <div>
          <p className="mb-1.5 text-osce-meta text-b2c-text-muted">
            How would you rate your overall experience? Optional.
          </p>
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((rating) => (
              <button
                key={rating}
                type="button"
                aria-label={`${rating} star${rating === 1 ? "" : "s"}`}
                aria-pressed={experienceRating === rating}
                onClick={() => setExperienceRating(rating)}
                className={`inline-flex h-11 w-11 items-center justify-center transition-all ${experienceRating && rating <= experienceRating ? "text-osce-warning-icon" : "text-b2c-text-muted hover:text-osce-warning-icon"}`}
              >
                <HiOutlineStar className="h-6 w-6" />
              </button>
            ))}
          </div>
          {experienceRating && (
            <p className="mt-1 text-osce-meta text-b2c-text-muted">
              {RATING_LABELS[experienceRating]}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="feedback-text" className="mb-1.5 block text-osce-meta text-b2c-text-muted">
            Additional feedback
          </label>
          <textarea
            id="feedback-text"
            value={feedbackText}
            onChange={(event) => setFeedbackText(event.target.value)}
            placeholder="Share any thoughts, suggestions, or feedback about your experience..."
            className={productTokens.b2cSettingsFieldInput}
            rows={3}
            maxLength={500}
          />
          <p className="mt-1 text-osce-meta text-b2c-text-muted">Optional. {feedbackText.length}/500 characters</p>
        </div>

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-osce-danger/30 bg-osce-danger-bg px-3 py-2.5 text-osce-body text-osce-danger-hover sm:px-4 sm:py-3"
          >
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onDone} disabled={isSubmitting}>
            Skip
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Submit feedback
          </Button>
        </div>
      </form>
    </section>
  );
}
