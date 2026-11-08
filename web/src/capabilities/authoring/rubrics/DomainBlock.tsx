"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import { markedLiveLabel } from "@/capabilities/authoring/lib/authoringCopy";
import { Switch, Textarea, cn, getInputClassName } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { FeedbackRows } from "@/capabilities/authoring/rubrics/FeedbackBlock";
import {
  isNumberScale,
  levelWord,
  scaleOf,
  updateBlock,
  updateCompetency,
  type DomainBlock,
  type NotesBlock,
  type Scheme,
} from "@/capabilities/authoring/rubrics/schemeModel";

interface DetailProps {
  scheme: Scheme;
  onScheme: (s: Scheme) => void;
  readOnly: boolean;
  onEditCustom: () => void;
  onDelete: () => void;
}

function Instructions({ value, path, readOnly, onChange }: { value: string; path: string; readOnly: boolean; onChange: (v: string) => void }) {
  return (
    <label className="block text-osce-caption font-medium text-ink-muted">
      Instructions
      <Textarea data-path={path} className="mt-1 min-h-24 font-normal" readOnly={readOnly} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

/** The detail of a domain: its instructions, switches and the feedback written once per domain. */
export function DomainDetail({ scheme, onScheme, readOnly, onEditCustom, onDelete, i }: DetailProps & { i: number }) {
  const w = useAssessWords();
  const block = scheme.outline[i] as DomainBlock;
  const base = `outline[${i}]`;
  return (
    <div className="space-y-4">
      <h3 className="text-osce-body font-semibold text-ink">{block.title || "Domain"}</h3>
      <Instructions value={block.instructions ?? ""} path={`${base}.instructions`} readOnly={readOnly} onChange={(v) => onScheme(updateBlock(scheme, i, { instructions: v }))} />
      <div className="flex items-center gap-3">
        <Switch label={markedLiveLabel(w)} checked={block.live === true} disabled={readOnly} onChange={(v) => onScheme(updateBlock(scheme, i, { live: v }))} />
        <span className="text-osce-body text-ink">{markedLiveLabel(w)}</span>
      </div>
      <div className="flex items-center gap-3">
        <Switch label="Optional: the marker may skip this domain" checked={block.optional === true} disabled={readOnly} onChange={(v) => onScheme(updateBlock(scheme, i, { optional: v }))} />
        <span className="text-osce-body text-ink">Optional: the marker may skip this domain</span>
      </div>
      <section className="space-y-2">
        <h4 className="text-osce-body font-semibold text-ink">Feedback the marker writes once for this domain</h4>
        <FeedbackRows items={block.feedback ?? []} where={{ level: "domain", blockIndex: i }} scheme={scheme} onScheme={onScheme} readOnly={readOnly} onEditCustom={onEditCustom} />
      </section>
      {readOnly ? null : (
        <AuthoringButton variant="ghost" size="sm" onClick={onDelete}>
          Delete domain
        </AuthoringButton>
      )}
    </div>
  );
}

/** The detail of a competency: instructions and what earns each level. */
export function CompetencyDetail({ scheme, onScheme, readOnly, onDelete, i, j }: Omit<DetailProps, "onEditCustom"> & { i: number; j: number }) {
  const block = scheme.outline[i] as DomainBlock;
  const competency = block.competencies[j];
  const scale = scaleOf(scheme, block);
  const base = `outline[${i}].competencies[${j}]`;
  if (!competency) return null;
  return (
    <div className="space-y-4">
      <h3 className="text-osce-body font-semibold text-ink">{competency.label || "Competency"}</h3>
      <Instructions value={competency.instructions ?? ""} path={`${base}.instructions`} readOnly={readOnly} onChange={(v) => onScheme(updateCompetency(scheme, i, j, { instructions: v }))} />
      {scale && !isNumberScale(scale) ? (
        <section className="space-y-2">
          <h4 className="text-osce-body font-semibold text-ink">What earns each level</h4>
          {scale.levels.map((level) => {
            const key = String(level.value);
            return (
              <label key={key} className="block text-osce-caption font-medium text-ink-muted">
                {levelWord(level)}
                <input
                  data-path={`${base}.descriptors.${key}`}
                  className={cn(getInputClassName({ size: "sm" }), "mt-1 font-normal")}
                  readOnly={readOnly}
                  value={competency.descriptors?.[key] ?? ""}
                  onChange={(event) => onScheme(updateCompetency(scheme, i, j, { descriptors: { ...(competency.descriptors ?? {}), [key]: event.target.value } }))}
                />
              </label>
            );
          })}
        </section>
      ) : null}
      {readOnly || block.competencies.length <= 1 ? (
        block.competencies.length <= 1 ? <p className="text-osce-caption text-ink-subtle">A domain keeps at least one competency.</p> : null
      ) : (
        <AuthoringButton variant="ghost" size="sm" onClick={onDelete}>
          Delete competency
        </AuthoringButton>
      )}
    </div>
  );
}

/** The detail of a notes block. */
export function NotesDetail({ scheme, onScheme, readOnly, onEditCustom, onDelete, i }: DetailProps & { i: number }) {
  const block = scheme.outline[i] as NotesBlock;
  return (
    <div className="space-y-4">
      <h3 className="text-osce-body font-semibold text-ink">{block.title || "Notes"}</h3>
      <Instructions value={block.instructions ?? ""} path={`outline[${i}].instructions`} readOnly={readOnly} onChange={(v) => onScheme(updateBlock(scheme, i, { instructions: v }))} />
      <section className="space-y-2">
        <h4 className="text-osce-body font-semibold text-ink">Feedback</h4>
        <FeedbackRows items={block.feedback} where={{ level: "notes", blockIndex: i }} scheme={scheme} onScheme={onScheme} readOnly={readOnly} onEditCustom={onEditCustom} />
      </section>
      {readOnly ? null : (
        <AuthoringButton variant="ghost" size="sm" onClick={onDelete}>
          Delete notes
        </AuthoringButton>
      )}
    </div>
  );
}

/** A block the form cannot show: it is kept as it is and edited as JSON. */
export function CustomDetail({ onEditCustom }: { onEditCustom: () => void }) {
  return (
    <div className="space-y-3">
      <p className="text-osce-body text-ink-muted">This part has settings the builder cannot display. They are kept as they are. Edit them on the Advanced tab if needed.</p>
      <AuthoringButton variant="secondary" size="sm" onClick={onEditCustom}>
        Edit in Advanced
      </AuthoringButton>
    </div>
  );
}
