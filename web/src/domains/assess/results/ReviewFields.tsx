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
      <ul className="divide-y divide-b2b-border">
        {domains.map((domain) => {
          // A domain-level field repeats the domain's name, so its rating sits
          // in the domain's own heading row; competency fields get a row each.
          const own = domain.fields.filter((field) => field.competency_id === null || field.competency_id === undefined);
          const parts = domain.fields.filter((field) => field.competency_id !== null && field.competency_id !== undefined);
          const input = (field: (typeof domain.fields)[number]) => (
            <RatingInput
              rating={form.rating}
              label={field.label}
              value={ratings[field.path] ?? null}
              disabled={disabled}
              onChange={(value) => onRate(field.path, value)}
            />
          );
          const machineNote = (path: string) => {
            const machine = machineRating(form.rating, payload, path);
            return machine !== null ? (
              <span className="text-osce-meta text-b2b-mid">Machine: {ratingLabel(form.rating, machine)}</span>
            ) : null;
          };
          return (
            <li key={domain.id} className="space-y-2 py-4 first:pt-0 last:pb-0">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className={b2bTokens.b2bSectionTitle}>{domain.label}</span>
                  {domain.required ? <Badge variant="neutral" size="xs">Required</Badge> : null}
                </div>
                {own.map((field) => (
                  <div key={field.path} className="flex flex-wrap items-center gap-3">
                    {machineNote(field.path)}
                    {input(field)}
                  </div>
                ))}
              </div>
              {parts.map((field) => (
                <div key={field.path} className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex min-w-0 flex-col">
                    <span className="text-osce-body text-b2b-headline">{field.label}</span>
                    {machineNote(field.path)}
                  </div>
                  {input(field)}
                </div>
              ))}
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
          );
        })}
      </ul>
      {missing.length > 0 ? (
        <p className="text-osce-meta text-b2b-mid">
          Still to rate before completing: {missing.join(", ")}.
        </p>
      ) : null}
    </div>
  );
}
