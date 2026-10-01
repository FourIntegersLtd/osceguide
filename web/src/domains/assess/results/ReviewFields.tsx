"use client";

import { Badge, b2bTokens } from "@/foundation/ui";
import { ratingLabel, type RatingValue } from "@/capabilities/feedback/rubric";
import { RatingInput } from "@/domains/assess/results/RatingInput";
import { formDomains, machineRating, unratedRequired, type ReviewForm } from "@/domains/assess/results/reviewForm";

/**
 * The rateable fields of a review form, domain by domain.
 *
 * Shared by the examiner's own review and the GP lead's: both rate the same
 * paths from the same `ReviewFormRead`. Each field shows the machine's rating
 * at that path beside the input, so a marker agrees or disagrees with it
 * rather than marking blind. The lead also writes a note per domain; the
 * examiner does not, so `comments` is optional.
 */
export function ReviewFields({
  form,
  ratings,
  onRate,
  payload,
  comments,
  onComment,
  disabled,
}: {
  form: ReviewForm | null | undefined;
  ratings: Record<string, RatingValue>;
  onRate: (path: string, value: RatingValue) => void;
  /** The machine's marked payload, read at each field's path. */
  payload: Record<string, unknown> | null;
  comments?: Record<string, string>;
  onComment?: (domainId: string, text: string) => void;
  disabled?: boolean;
}) {
  const domains = formDomains(form);
  if (!form || domains.length === 0) {
    return (
      <p className="text-osce-body text-b2b-mid">
        This station&rsquo;s marking scheme has nothing to rate, so there is nothing to agree or disagree with. Your notes are still saved.
      </p>
    );
  }

  const missing = unratedRequired(form, ratings);

  return (
    <div className="space-y-4">
      <ul className="space-y-5">
        {domains.map((domain) => (
          <li key={domain.id} className="space-y-2.5">
            <div className="flex items-center gap-2">
              <span className={b2bTokens.b2bSectionTitle}>{domain.label}</span>
              {domain.required ? <Badge variant="neutral" size="xs">Required</Badge> : null}
            </div>
            {domain.fields.map((field) => {
              const machine = machineRating(form.rating, payload, field.path);
              // A domain-level field repeats the domain's name; say nothing twice.
              const showLabel = field.competency_id !== null && field.competency_id !== undefined;
              return (
                <div key={field.path} className="space-y-1.5">
                  <div className="flex items-center justify-between gap-3">
                    {showLabel ? (
                      <span className="text-osce-caption font-medium text-b2b-headline">{field.label}</span>
                    ) : (
                      <span />
                    )}
                    {machine !== null ? (
                      <span className="shrink-0 text-osce-caption text-b2b-mid">
                        machine: {ratingLabel(form.rating, machine)}
                      </span>
                    ) : null}
                  </div>
                  <RatingInput
                    rating={form.rating}
                    label={field.label}
                    value={ratings[field.path] ?? null}
                    disabled={disabled}
                    onChange={(value) => onRate(field.path, value)}
                  />
                </div>
              );
            })}
            {comments && onComment ? (
              <label className="block">
                <span className="sr-only">Note on {domain.label}</span>
                <textarea
                  rows={2}
                  value={comments[domain.id] ?? ""}
                  disabled={disabled}
                  onChange={(event) => onComment(domain.id, event.target.value)}
                  placeholder={`Why this rating for ${domain.label}`}
                  className={`${b2bTokens.b2bInputBase} w-full`}
                />
              </label>
            ) : null}
          </li>
        ))}
      </ul>
      {missing.length > 0 ? (
        <p className="text-osce-caption text-b2b-mid">
          Still to rate before completing: {missing.join(", ")}.
        </p>
      ) : null}
    </div>
  );
}
