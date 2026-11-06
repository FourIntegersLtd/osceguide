"use client";

import { Select, Switch, cn, getInputClassName } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import {
  FEEDBACK_KIND_WORDS,
  FEEDBACK_SHAPE_WORDS,
  SHOW_KEYS,
  SHOW_WORDS,
  TONE_WORDS,
  addFeedback,
  isCustom,
  removeFeedback,
  setShow,
  setTone,
  updateFeedback,
  type Feedback,
  type FeedbackKind,
  type FeedbackShape,
  type FeedbackWhere,
  type Problem,
  type Scheme,
} from "@/capabilities/authoring/rubrics/schemeModel";

/** The rows of one feedback list; a custom item is a grey read-only row. */
export function FeedbackRows({
  items,
  where,
  scheme,
  onScheme,
  readOnly,
  onEditCustom,
}: {
  items: readonly Feedback[];
  where: FeedbackWhere;
  scheme: Scheme;
  onScheme: (s: Scheme) => void;
  readOnly: boolean;
  onEditCustom: () => void;
}) {
  return (
    <div className="space-y-2">
      {items.map((item, k) =>
        isCustom(item) ? (
          <div key={`${item.id ?? "custom"}-${k}`} className="flex flex-wrap items-center gap-2 rounded-osce-md bg-osce-canvas px-3 py-2 text-osce-meta text-ink-muted">
            <span className="flex-1">{item.id ?? "Custom field"}</span>
            <span>Custom field, edit in Advanced</span>
            <AuthoringButton variant="ghost" size="sm" onClick={onEditCustom}>
              Edit in Advanced
            </AuthoringButton>
          </div>
        ) : (
          <div key={`${item.id}-${k}`} className="grid grid-cols-1 items-center gap-2 sm:grid-cols-[minmax(0,1fr)_200px_150px_auto]">
            <input
              aria-label="Name"
              className={cn(getInputClassName({ size: "sm" }), "min-w-0")}
              readOnly={readOnly}
              value={item.label ?? ""}
              onChange={(event) => onScheme(updateFeedback(scheme, where, k, { label: event.target.value }))}
            />
            <Select selectSize="sm" aria-label="What it is" disabled={readOnly} value={item.kind} onChange={(event) => onScheme(updateFeedback(scheme, where, k, { kind: event.target.value as FeedbackKind }))}>
              {(Object.keys(FEEDBACK_KIND_WORDS) as FeedbackKind[]).map((kind) => (
                <option key={kind} value={kind}>{FEEDBACK_KIND_WORDS[kind]}</option>
              ))}
            </Select>
            <Select selectSize="sm" aria-label="Written as" disabled={readOnly} value={item.shape} onChange={(event) => onScheme(updateFeedback(scheme, where, k, { shape: event.target.value as FeedbackShape }))}>
              {(Object.keys(FEEDBACK_SHAPE_WORDS) as FeedbackShape[]).map((shape) => (
                <option key={shape} value={shape}>{FEEDBACK_SHAPE_WORDS[shape]}</option>
              ))}
            </Select>
            {readOnly ? null : (
              <AuthoringButton variant="ghost" size="sm" onClick={() => onScheme(removeFeedback(scheme, where, k))}>
                Remove
              </AuthoringButton>
            )}
          </div>
        ),
      )}
      {readOnly ? null : (
        <AuthoringButton variant="ghost" size="sm" onClick={() => onScheme(addFeedback(scheme, where))}>
          Add feedback
        </AuthoringButton>
      )}
    </div>
  );
}

/** What the marker writes for every competency, what the candidate sees, and the tone. */
export function FeedbackBlock({ scheme, onScheme, readOnly, problems, onEditCustom }: { scheme: Scheme; onScheme: (s: Scheme) => void; readOnly: boolean; problems: readonly Problem[]; onEditCustom: () => void }) {
  const own = problems.filter((p) => p.path.startsWith("competencyFeedback") || p.path.startsWith("show") || p.path === "tone");
  return (
    <div className="space-y-6" data-path="competencyFeedback">
      <div>
        <h2 className="text-osce-body font-semibold text-ink">Feedback</h2>
        <p className="text-osce-caption text-ink-muted">What the marker writes, and what the candidate sees.</p>
      </div>
      <section className="space-y-2">
        <h3 className="text-osce-body font-semibold text-ink">Feedback the marker writes for every competency</h3>
        <FeedbackRows items={scheme.competencyFeedback ?? []} where={{ level: "competency" }} scheme={scheme} onScheme={onScheme} readOnly={readOnly} onEditCustom={onEditCustom} />
        <p className="text-osce-caption text-ink-muted">The rating itself is always asked for; it is not in this list.</p>
      </section>
      <section className="space-y-1" data-path="show">
        <h3 className="text-osce-body font-semibold text-ink">What the candidate sees</h3>
        {SHOW_KEYS.map((key) => {
          const on = scheme.show?.[key] !== false;
          return (
            <div key={key} className="flex items-center gap-3 border-t border-osce-border-light py-2 first:border-t-0">
              <Switch label={SHOW_WORDS[key].label} checked={on} disabled={readOnly} onChange={(next) => onScheme(setShow(scheme, key, next))} />
              <div className="min-w-0 flex-1">
                <div className="text-osce-body font-medium text-ink">{SHOW_WORDS[key].label}</div>
                <div className="text-osce-caption text-ink-muted">{SHOW_WORDS[key].hint}</div>
              </div>
              <span className="text-osce-caption text-ink-subtle">{on ? "Shown" : "Hidden"}</span>
            </div>
          );
        })}
        <p className="text-osce-caption text-ink-muted">Watch the preview change as you switch these.</p>
      </section>
      <section className="space-y-2" data-path="tone">
        <h3 className="text-osce-body font-semibold text-ink">Tone</h3>
        <div role="radiogroup" aria-label="Tone" className="flex flex-wrap gap-2">
          {TONE_WORDS.map((tone) => {
            const on = (scheme.tone ?? null) === tone.value;
            return (
              <button
                key={tone.label}
                type="button"
                role="radio"
                aria-checked={on}
                disabled={readOnly}
                onClick={() => onScheme(setTone(scheme, tone.value))}
                className={cn("min-h-9 rounded-full border px-3.5 text-osce-meta", on ? "border-accent bg-osce-accent-subtle font-medium text-ink" : "border-osce-border text-ink-muted")}
              >
                {tone.label}
              </button>
            );
          })}
        </div>
        <p className="text-osce-caption text-ink-muted">{TONE_WORDS.find((t) => (scheme.tone ?? null) === t.value)?.hint}</p>
      </section>
      {own.map((p) => (
        <p key={`${p.path}-${p.message}`} className="text-osce-caption text-osce-danger-text">{p.message}</p>
      ))}
    </div>
  );
}
