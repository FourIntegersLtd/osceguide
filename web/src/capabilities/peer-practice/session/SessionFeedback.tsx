"use client";

import { useState, type FormEvent } from "react";
import { HiOutlineArrowPath, HiOutlineStar } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { b2cCard, b2cCardPadding } from "@/foundation/ui/productTokens";
import { submitPracticeFeedback } from "../api";
import { failureText } from "../support/failure";

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
    <div className={`mx-auto max-w-2xl text-left ${b2cCard} ${b2cCardPadding}`}>
      <div className="mb-4 sm:mb-6">
        <h3 className="mb-2 text-osce-body font-bold text-osce-ink-900">Colleague Practice Session Feedback</h3>
        <p className="text-osce-body text-b2c-text-secondary">
          Help us improve! Your feedback helps us match you with better practice partners and enhance the experience.
        </p>
      </div>
      <form onSubmit={(event) => void submit(event)} className="space-y-4 sm:space-y-6">
        <div>
          <p className="mb-2 block text-osce-body font-semibold text-osce-ink-900 sm:mb-3">
            Would you practice with this user again? <span className="text-osce-danger">*</span>
          </p>
          <div className="flex flex-col gap-2 sm:flex-row sm:gap-4">
            <button
              type="button"
              aria-pressed={wouldPracticeAgain === true}
              onClick={() => setWouldPracticeAgain(true)}
              className={`flex-1 rounded-lg border-2 px-3 py-2.5 text-osce-body transition-all sm:px-4 sm:py-3 ${wouldPracticeAgain === true ? "border-osce-accent bg-osce-accent-muted font-semibold text-osce-accent-hover" : "border-b2c-border bg-b2c-surface-muted text-b2c-text-secondary hover:border-osce-accent-light"}`}
            >
              Yes
            </button>
            <button
              type="button"
              aria-pressed={wouldPracticeAgain === false}
              onClick={() => setWouldPracticeAgain(false)}
              className={`flex-1 rounded-lg border-2 px-3 py-2.5 text-osce-body transition-all sm:px-4 sm:py-3 ${wouldPracticeAgain === false ? "border-osce-danger bg-osce-danger-bg font-semibold text-osce-danger-hover" : "border-b2c-border bg-b2c-surface-muted text-b2c-text-secondary hover:border-osce-danger"}`}
            >
              No
            </button>
          </div>
        </div>

        <div>
          <p className="mb-2 block text-osce-body font-semibold text-osce-ink-900 sm:mb-3">
            How would you rate your overall experience? (Optional)
          </p>
          <div className="flex justify-center gap-1 sm:justify-start sm:gap-2">
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
            <p className="mt-1 text-center text-osce-body text-b2c-text-muted sm:text-left">
              {RATING_LABELS[experienceRating]}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="feedback-text" className="mb-2 block text-osce-body font-semibold text-osce-ink-900">
            Additional feedback (Optional)
          </label>
          <textarea
            id="feedback-text"
            value={feedbackText}
            onChange={(event) => setFeedbackText(event.target.value)}
            placeholder="Share any thoughts, suggestions, or feedback about your experience..."
            className="w-full resize-none rounded-lg border border-b2c-border px-3 py-2.5 text-osce-body sm:px-4 sm:py-3"
            rows={3}
            maxLength={500}
          />
          <p className="mt-1 text-osce-body text-b2c-text-muted">{feedbackText.length}/500 characters</p>
        </div>

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-osce-danger/30 bg-osce-danger-bg px-3 py-2.5 text-osce-body text-osce-danger-hover sm:px-4 sm:py-3"
          >
            {error}
          </div>
        )}

        <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
          <Button type="submit" variant="commit" size="md" disabled={isSubmitting} className="flex-1 gap-2">
            {isSubmitting ? (
              <>
                <HiOutlineArrowPath className="h-3 w-3 animate-spin sm:h-4 sm:w-4" />
                <span>Submitting...</span>
              </>
            ) : (
              <>Submit Feedback</>
            )}
          </Button>
          <Button type="button" variant="secondary" size="md" onClick={onDone} disabled={isSubmitting}>
            Skip
          </Button>
        </div>
      </form>
    </div>
  );
}
