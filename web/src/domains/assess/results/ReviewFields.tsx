"use client";

import { b2bTokens } from "@/foundation/ui";
import { ratingLabel, type RatingValue } from "@/capabilities/feedback/rubric";
import { RatingInput } from "@/domains/assess/results/RatingInput";
import { formDomains, machineRating, unratedRequired, type ReviewForm } from "@/domains/assess/results/reviewForm";
import { boardInput } from "@/foundation/ui/boardKit";

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
      <p className="text-assess-label text-osce-ink-500">
        This station&rsquo;s marking scheme has nothing to rate, so there is nothing to agree or disagree with. Your notes are still saved.
      </p>
    );
  }

  const missing = unratedRequired(form, ratings);

  return (
    <div className="flex flex-col gap-6">
      <ul>
        {domains.map((domain) => {
          // A domain-level field repeats the domain's name, so its rating sits
          // in the domain's own row; competency fields get a row each beneath it.
          const own = domain.fields.find((field) => field.competency_id === null || field.competency_id === undefined);
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
              <div className="text-assess-meta text-osce-ink-500">Machine: {ratingLabel(form.rating, machine)}</div>
            ) : null;
          };
          return (
            <li key={domain.id} className="border-t border-osce-border-light">
              <div className={ROW}>
                <div className="min-w-0 flex-[1_1_180px]">
                  <div className="font-medium">
                    {domain.label}{" "}
                    {domain.required ? <span className={b2bTokens.assessChipNeutral}>Required</span> : null}
                  </div>
                  {own ? machineNote(own.path) : null}
                </div>
                {own ? input(own) : null}
              </div>
              {parts.map((field) => (
                <div key={field.path} className={`${ROW} border-t border-osce-border-light pl-4`}>
                  <div className="min-w-0 flex-[1_1_180px]">
                    <div>{field.label}</div>
                    {machineNote(field.path)}
                  </div>
                  {input(field)}
                </div>
              ))}
              {comments && onComment ? (
                <label className="block pb-3">
                  <span className="sr-only">Note on {domain.label}</span>
                  <input
                    type="text"
                    value={comments[domain.id] ?? ""}
                    disabled={disabled}
                    onChange={(event) => onComment(domain.id, event.target.value)}
                    placeholder={`Why this rating for ${domain.label}`}
                    className={boardInput}
                  />
                </label>
              ) : null}
            </li>
          );
        })}
      </ul>
      {missing.length > 0 ? (
        <p className="text-assess-meta text-osce-ink-500">
          Still to rate before completing: {missing.join(", ")}.
        </p>
      ) : null}
    </div>
  );
}

/** The board's `.row` inside a card: 12px above and below, no side padding. */
const ROW = "flex flex-wrap items-center gap-4 py-4 text-assess-label text-osce-ink-900";
