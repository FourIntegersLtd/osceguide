"use client";

import { useState, type ReactNode } from "react";
import { LuMessageSquare } from "react-icons/lu";
import { Alert, Button, ModalHelper, ModalTitle, cn, productTokens, Panel } from "@/foundation/ui";
import { useToast } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { sendSiteMessage } from "@/capabilities/help/api";
import { StarRating, TestimonialChoice } from "@/capabilities/help/ProductFeedbackFields";
import {
  composeFeedbackBody,
  type ProductFeedbackSource,
  type TestimonialPermission,
} from "@/capabilities/help/productFeedbackModel";

const { b2cFieldLabel, b2cSettingsFieldInput } = productTokens;

/*
 * A straight port of the retiring client's `ProductFeedbackForm` — the stars,
 * the experience box, the testimonial question and the exact copy. What
 * changed is the wire: the old form composed one text blob and posted it to
 * `/api/create_message`; `POST /site/messages` has a `kind` of its own for
 * this ("product_feedback"), so the message is filed as feedback while the
 * body keeps the old composition (`composeFeedbackBody`).
 *
 * The old form also marked a browser-storage flag that suppressed an
 * in-product feedback prompt afterwards. That prompt mechanism has not been
 * ported (the `pending-feedback` capability is a different thing — feedback
 * owed on a finished session), so there is no flag to mark.
 */

const compactFieldClass =
  "mt-1.5 w-full rounded-md border border-b2c-border bg-osce-surface px-3 py-2.5 text-osce-body text-osce-ink-900 placeholder:text-b2c-text-muted focus:border-osce-accent focus:outline-none focus:ring-2 focus:ring-osce-accent-subtle";

export type ProductFeedbackFormProps = {
  source: ProductFeedbackSource;
  /** Show centered intro icon + title (modal). Page tabs can hide and supply their own. */
  showIntro?: boolean;
  /** Wrap fields in a panel card with header + bottom-right footer action. */
  cardTitle?: string;
  /** Shorter copy and denser layout for session-end. */
  compact?: boolean;
  onSubmitted?: () => void;
  className?: string;
};

export type { ProductFeedbackSource, TestimonialPermission };

export function ProductFeedbackForm({
  source,
  showIntro = true,
  cardTitle,
  compact = false,
  onSubmitted,
  className = "",
}: ProductFeedbackFormProps) {
  const { session } = useSession();
  const toast = useToast();
  const [rating, setRating] = useState(0);
  const [experience, setExperience] = useState("");
  const [testimonialPermission, setTestimonialPermission] =
    useState<TestimonialPermission | "">("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const idPrefix = `product-feedback-${source}`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const email = session?.user.email.trim() ?? "";
    if (!email) {
      setError("Please sign in to send feedback.");
      return;
    }
    if (rating < 1) {
      setError("Please rate your experience.");
      return;
    }
    if (!testimonialPermission) {
      setError("Please choose a testimonial preference.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const stars = Math.min(5, Math.max(1, Math.round(rating)));
      const name = session?.user.name.trim() || "";
      await sendSiteMessage({
        kind: "product_feedback",
        name: name || null,
        email,
        subject: `Product feedback. ${stars}/5`,
        body: composeFeedbackBody({
          name,
          email,
          rating: stars,
          testimonialPermission,
          source,
          examCode: session?.user.exam_code ?? undefined,
          experience: experience.trim(),
        }),
        source,
      });
      toast.success("Feedback sent", "Thanks for helping us improve.");
      setRating(0);
      setExperience("");
      setTestimonialPermission("");
      onSubmitted?.();
    } catch {
      setError("Could not send feedback. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const submitButton = (
    <Button type="submit" isLoading={loading}>
      Send
    </Button>
  );

  const fields: ReactNode = (
    <>
      {error ? <Alert tone="danger">{error}</Alert> : null}

      <div>
        <p
          className={cn(
            "font-medium text-b2c-text-secondary",
            compact ? "mb-2 text-osce-meta" : "mb-3 text-osce-body leading-snug",
          )}
        >
          {compact ? (
            <>
              Rating <span className="text-osce-danger">*</span>
            </>
          ) : (
            <>
              How would you rate your experience with the OSCE Guide app?{" "}
              <span className="text-osce-danger">*</span>
            </>
          )}
        </p>
        <StarRating value={rating} onChange={setRating} compact={compact} />
        {!compact ? (
          <div className="mt-2 flex justify-between text-osce-meta text-b2c-text-muted">
            <span>Poor</span>
            <span>Excellent</span>
          </div>
        ) : null}
      </div>

      <div>
        <label
          htmlFor={`${idPrefix}-experience`}
          className={
            compact
              ? "text-osce-meta font-medium text-b2c-text-secondary"
              : b2cFieldLabel
          }
        >
          {compact
            ? "Anything to share?"
            : "Tell us about your experience with OSCE Guide"}
        </label>
        <textarea
          id={`${idPrefix}-experience`}
          value={experience}
          onChange={(e) => setExperience(e.target.value)}
          placeholder={
            compact ? "Optional" : "What worked well? What could be better?"
          }
          rows={compact ? 3 : 5}
          maxLength={4000}
          className={cn(
            "mt-1.5 resize-y",
            compact ? compactFieldClass : b2cSettingsFieldInput,
          )}
        />
      </div>

      <TestimonialChoice
        idPrefix={idPrefix}
        value={testimonialPermission}
        onChange={setTestimonialPermission}
        compact={compact}
      />
    </>
  );

  return (
    <div className={cn(compact ? "space-y-3" : "space-y-6", className)}>
      {showIntro ? (
        <div className="flex flex-col items-center text-center">
          <span className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-osce-accent-muted text-osce-accent">
            <LuMessageSquare className="h-5 w-5" aria-hidden />
          </span>
          <ModalTitle className="text-osce-body">
            We&apos;d love your feedback
          </ModalTitle>
          <ModalHelper className="mt-1">
            Your feedback helps us improve OSCE Guide. With your permission, we
            may also feature it as a testimonial.
          </ModalHelper>
        </div>
      ) : null}

      {compact && !cardTitle ? (
        <p className="text-osce-meta font-medium text-b2c-text-secondary">
          Feedback
        </p>
      ) : null}

      <form
        className={cn(compact ? "space-y-3" : "space-y-6")}
        onSubmit={handleSubmit}
      >
        {cardTitle ? (
          <Panel title={cardTitle} description="Your feedback helps us improve.">
            <div className={compact ? "space-y-4" : "space-y-5"}>
              {fields}
              <div>{submitButton}</div>
            </div>
          </Panel>
        ) : (
          <>
            {fields}
            <div className="flex justify-end pt-1">{submitButton}</div>
          </>
        )}
      </form>
    </div>
  );
}
