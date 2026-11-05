"use client";

import { useId } from "react";
import { StructureBuilder } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/StructureBuilder";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { cn, getInputClassName, Textarea, FoldSection } from "@/foundation/ui";

/** The four pacing numbers a rubric's station runs on, in seconds. */
export const PACING_KEYS = [
  { key: "total_seconds", label: "Whole station", hint: "How long the station lasts." },
  { key: "introduction_seconds", label: "Introduction ends", hint: "Must come before history ends." },
  { key: "history_seconds", label: "History ends", hint: "When the patient moves on from history." },
  { key: "safety_net_seconds", label: "Safety-net window", hint: "The last stretch, counted back from the end." },
] as const;

export type Pacing = Record<string, unknown>;

/**
 * What the marking model is told, how long the station runs, and the form a
 * human examiner fills in — the parts of a version that are not the result
 * structure. The backend checks pacing when the draft is saved and the prompt
 * and examiner layout when it is published, so their problems arrive as a
 * save or publish error rather than inline.
 */
export function MarkingPanel({
  systemPrompt,
  onSystemPrompt,
  pacing,
  onPacing,
  markingLayout,
  onMarkingLayout,
  title,
  readOnly,
  layoutRequired,
  draft,
}: {
  systemPrompt: string;
  onSystemPrompt: (value: string) => void;
  pacing: Pacing;
  onPacing: (value: Pacing) => void;
  markingLayout: StationStructure;
  onMarkingLayout: (value: StationStructure) => void;
  title: string;
  readOnly: boolean;
  /** Platform catalogue rubrics need an examiner layout before they can be published. */
  layoutRequired: boolean;
  /** Fill the instructions from the areas above (backend draft-instructions). */
  draft: { run: () => void; busy: boolean; allowed: boolean };
}) {
  const promptId = useId();
  return (
    <div className="space-y-6">
      <FoldSection title="Marking instructions" description="Written for the AI marker and for supervisors.">
        {!readOnly ? (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <p className="text-osce-caption text-ink-muted">Draft them for me from the areas above, then edit.</p>
            <AuthoringButton variant="ghost" size="sm" isLoading={draft.busy} disabled={!draft.allowed || draft.busy} onClick={draft.run}>
              Draft them for me
            </AuthoringButton>
          </div>
        ) : null}
        <label htmlFor={promptId} className="sr-only">
          Marking instructions (system prompt)
        </label>
        <Textarea
          id={promptId}
          textareaSize="sm"
          invalid={systemPrompt.trim() === ""}
          rows={10}
          readOnly={readOnly}
          value={systemPrompt}
          onChange={(event) => onSystemPrompt(event.target.value)}
          className="mt-1 font-mono"
        />
        <p className="mt-0.5 text-osce-caption text-ink-subtle">
          What the marking model reads before the transcript. A version cannot be published without it.
        </p>
      </FoldSection>

      <FoldSection title="Pacing, in seconds">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
          {PACING_KEYS.map((item) => (
            <label key={item.key} className="block">
              <span className="block text-osce-caption font-medium text-ink-muted">{item.label}</span>
              <input
                type="number"
                min={0}
                step={1}
                readOnly={readOnly}
                value={typeof pacing[item.key] === "number" ? (pacing[item.key] as number) : ""}
                onChange={(event) => {
                  const text = event.target.value;
                  onPacing({ ...pacing, [item.key]: text === "" ? undefined : Number(text) });
                }}
                className={cn(getInputClassName({ size: "sm" }), "mt-1")}
              />
              <span className="mt-0.5 block text-osce-caption text-ink-subtle">{item.hint}</span>
            </label>
          ))}
        </div>
      </FoldSection>

      <FoldSection title="Examiner layout">
        <p className="text-osce-caption text-ink-subtle">
          The form a human reviewer fills in for a slot. What the supervisor sees when reviewing is set alongside.
          {layoutRequired ? " Platform catalogue marking schemes need one before they can be published." : ""}
        </p>
        <div className={cn("mt-3 rounded-osce-md border border-osce-border bg-osce-surface p-3", readOnly && "pointer-events-none opacity-80")}>
          <StructureBuilder kind="feedback" value={markingLayout} onChange={onMarkingLayout} title={title} />
        </div>
      </FoldSection>
    </div>
  );
}
