"use client";

import { useId } from "react";
import { cn, getInputClassName, FoldSection } from "@/foundation/ui";
import { useRubricBuilder } from "@/capabilities/authoring/rubrics/builderContext";
import { AddButton, NumberAtPath, ProblemNote, SelectAtPath } from "@/capabilities/authoring/rubrics/formParts";
import { problemsAt } from "@/capabilities/authoring/rubrics/problems";
import {
  identifierFrom,
  readRating,
  withRatingField,
  withRatingKind,
  withScale,
} from "@/capabilities/authoring/rubrics/rubricEdits";
import { RATING_KINDS } from "@/capabilities/authoring/rubrics/rubricVocabulary";

const STEP_CHOICES = [
  { value: "integer" as const, label: "Whole numbers", hint: "0, 1, 2 and so on, with no halves." },
  { value: "number" as const, label: "Any number", hint: "Halves and decimals allowed." },
];

/**
 * How every competency is rated: one rating for the whole rubric.
 *
 * Changing the kind goes through `withRatingKind`, which also drops what the
 * new kind refuses (tones on a graded scale, descriptors for grades that no
 * longer exist). Renaming the rating's field renames it in every domain, so
 * the two never disagree.
 */
export function RatingPanel() {
  const { structure, edit, problems, readOnly } = useRubricBuilder();
  const rating = readRating(structure);
  const fieldId = useId();
  const fieldMessages = problemsAt(problems, ["rating", "field"]);
  return (
    <div className="space-y-6">
      <div data-path="rating.kind">
        <FoldSection title="Rated as">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {RATING_KINDS.map((kind) => {
            const active = rating.kind === kind.value;
            return (
              <button
                key={kind.value}
                type="button"
                disabled={readOnly}
                aria-pressed={active}
                onClick={() => edit((current) => withRatingKind(current, kind.value))}
                className={cn(
                  "rounded-osce-md border p-3 text-left transition-colors",
                  active ? "border-osce-accent bg-osce-accent-subtle" : "border-osce-border bg-osce-surface hover:border-osce-accent",
                )}
              >
                <span className="block text-osce-body font-semibold text-ink">{kind.label}</span>
                <span className="mt-0.5 block text-osce-caption text-ink-muted">{kind.hint}</span>
              </button>
            );
          })}
        </div>
        <ProblemNote messages={[...problemsAt(problems, ["rating"]), ...problemsAt(problems, ["rating", "kind"])]} />
        </FoldSection>
      </div>

      <FoldSection title="Grades">
      <div className="space-y-6">
      <div className="max-w-sm">
        <label htmlFor={fieldId} className="block text-osce-meta font-medium text-ink-muted">
          Field name
        </label>
        <input
          id={fieldId}
          data-path="rating.field"
          readOnly={readOnly}
          value={rating.field}
          onChange={(event) => {
            const typed = event.target.value;
            edit((current) => withRatingField(current, typed));
          }}
          onBlur={() => edit((current) => withRatingField(current, identifierFrom(readRating(current).field, "score")))}
          className={cn("mt-1 font-mono", getInputClassName({ size: "sm", invalid: fieldMessages.length > 0 }))}
        />
        <p className="mt-0.5 text-osce-caption text-ink-subtle">
          What each competency&apos;s grade is stored as, e.g. <code>score</code>. Renamed in every domain.
        </p>
        <ProblemNote messages={fieldMessages} />
      </div>

      {rating.kind === "rag" ? (
        <p className="text-osce-meta text-ink-muted">Grades G, A and R, best first. Coloured green, amber and red.</p>
      ) : null}
      {rating.kind === "scale" ? <ScaleEditor scale={rating.scale} /> : null}
      {rating.kind === "range" ? (
        <div className="grid grid-cols-1 max-w-xl gap-3 sm:grid-cols-3">
          <NumberAtPath path={["rating", "minimum"]} label="Lowest" />
          <NumberAtPath path={["rating", "maximum"]} label="Highest" />
          <SelectAtPath path={["rating", "step"]} label="Values" choices={STEP_CHOICES} />
        </div>
      ) : null}
      {rating.kind === "boolean" ? (
        <p className="text-osce-meta text-ink-muted">Each competency is met or not met. Colour it on the Results tab with tones.</p>
      ) : null}
      </div>
      </FoldSection>
    </div>
  );
}

/** A named scale's grades, best first. Renaming a grade carries its descriptors with it. */
function ScaleEditor({ scale }: { scale: readonly string[] }) {
  const { edit, problems, readOnly } = useRubricBuilder();
  const replace = (next: string[]) => edit((current) => withScale(current, next));
  return (
    <div className="max-w-md space-y-2" data-path="rating.scale">
      <p className="text-osce-meta font-medium text-ink-muted">Grades, best first</p>
      {scale.map((grade, position) => (
        <div key={position} className="flex min-w-0 items-center gap-2">
          <span className="w-6 text-right text-osce-caption text-ink-subtle">{position + 1}</span>
          <input
            aria-label={`Grade ${position + 1}`}
            readOnly={readOnly}
            value={grade}
            onChange={(event) => replace(scale.map((existing, index) => (index === position ? event.target.value : existing)))}
            className={getInputClassName({ size: "sm" })}
          />
          {readOnly ? null : (
            <button
              type="button"
              aria-label={`Remove grade ${grade}`}
              onClick={() => replace(scale.filter((_existing, index) => index !== position))}
              className="rounded-osce-sm px-2 py-1 text-osce-caption text-ink-subtle hover:text-osce-danger"
            >
              Remove
            </button>
          )}
        </div>
      ))}
      <AddButton label="Add grade" onClick={() => replace([...scale, `Grade ${scale.length + 1}`])} />
      <ProblemNote messages={problemsAt(problems, ["rating", "scale"])} />
    </div>
  );
}
