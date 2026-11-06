"use client";

import { useId, useState } from "react";
import { StructureBuilder } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/StructureBuilder";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { parseSchemeJson, type Scheme } from "@/capabilities/authoring/rubrics/schemeModel";
import { Alert, cn, FoldSection, getInputClassName, Textarea } from "@/foundation/ui";

/** The four pacing numbers a rubric's station runs on, in seconds. */
const PACING_KEYS = [
  { key: "total_seconds", label: "Whole station", hint: "How long the station lasts." },
  { key: "introduction_seconds", label: "Introduction ends", hint: "Must come before history ends." },
  { key: "history_seconds", label: "History ends", hint: "When the patient moves on from history." },
  { key: "safety_net_seconds", label: "Safety-net window", hint: "The last stretch, counted back from the end." },
] as const;

export type Pacing = Record<string, unknown>;

/**
 * The Advanced tab: what the marking model is told, how long the station runs, the examiner's
 * layout, and the whole scheme as JSON for the parts the blocks cannot show.
 *
 * The backend checks pacing when the draft is saved and the instructions and layout when it is
 * published, so their problems arrive as a save or publish error rather than inline.
 */
export function AdvancedDisclosure({
  scheme,
  onScheme,
  systemPrompt,
  onSystemPrompt,
  pacing,
  onPacing,
  markingLayout,
  onMarkingLayout,
  readOnly,
  layoutRequired,
  draft,
  openJson,
  json,
}: {
  scheme: Scheme;
  onScheme: (s: Scheme) => void;
  systemPrompt: string;
  onSystemPrompt: (v: string) => void;
  pacing: Pacing;
  onPacing: (v: Pacing) => void;
  markingLayout: StationStructure;
  onMarkingLayout: (v: StationStructure) => void;
  readOnly: boolean;
  /** Platform catalogue rubrics need an examiner layout before they can be published. */
  layoutRequired: boolean;
  /** Fill the instructions from the domains (backend draft-instructions). */
  draft: { run: () => void; busy: boolean; allowed: boolean };
  /** Arrived from "Edit in Advanced" on a custom row, or a scheme the builder cannot show. */
  openJson: boolean;
  /** Text typed in the JSON editor and not yet applied; null when there is none. It outlives tab and scheme changes. */
  json: { text: string | null; onText: (text: string | null) => void };
}) {
  const promptId = useId();
  return (
    <div className="space-y-4" data-path="advanced">
      <FoldSection title="Marking instructions" description="Written for the AI marker and for supervisors.">
        {!readOnly ? (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <p className="text-osce-caption text-ink-muted">Draft them for me from the domains, then edit.</p>
            <AuthoringButton variant="secondary" size="sm" isLoading={draft.busy} disabled={!draft.allowed || draft.busy} onClick={draft.run}>
              Draft them for me
            </AuthoringButton>
          </div>
        ) : null}
        <label htmlFor={promptId} className="sr-only">
          Marking instructions
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
        {systemPrompt.trim() === "" ? <p className="mt-1 text-osce-caption text-osce-danger-text">Write the marking instructions, or press Draft them for me.</p> : null}
        <p className="mt-0.5 text-osce-caption text-ink-subtle">What the marking model reads before the transcript. A version cannot be published without it.</p>
      </FoldSection>

      <FoldSection title="Pacing, in seconds" defaultOpen={false}>
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
                onChange={(event) => onPacing({ ...pacing, [item.key]: event.target.value === "" ? undefined : Number(event.target.value) })}
                className={cn(getInputClassName({ size: "sm" }), "mt-1")}
              />
              <span className="mt-0.5 block text-osce-caption text-ink-subtle">{item.hint}</span>
            </label>
          ))}
        </div>
        <p className="mt-2 text-osce-caption text-ink-subtle">When the live supervisor prompts move on. Leave blank for none.</p>
      </FoldSection>

      <FoldSection title="Examiner layout" defaultOpen={false}>
        <p className="text-osce-caption text-ink-subtle">
          What the supervisor sees when reviewing a station, in order.
          {layoutRequired ? " Platform catalogue marking schemes need one before they can be published." : ""}
        </p>
        <div className={cn("mt-3 rounded-osce-md border border-osce-border bg-osce-surface p-3", readOnly && "pointer-events-none opacity-80")}>
          <StructureBuilder kind="feedback" value={markingLayout} onChange={onMarkingLayout} />
        </div>
      </FoldSection>

      <FoldSection title="Scheme as JSON" defaultOpen={openJson}>
        <SchemeJson scheme={scheme} onScheme={onScheme} readOnly={readOnly} typed={json.text} onTyped={json.onText} />
      </FoldSection>
    </div>
  );
}

/** The scheme, whole, as text. Applying it replaces the scheme; typed text stays until it is applied or discarded. */
function SchemeJson({ scheme, onScheme, readOnly, typed, onTyped }: { scheme: Scheme; onScheme: (s: Scheme) => void; readOnly: boolean; typed: string | null; onTyped: (text: string | null) => void }) {
  const [error, setError] = useState<string | null>(null);
  const apply = () => {
    const read = parseSchemeJson(typed ?? "");
    if ("error" in read) return setError(read.error);
    setError(null);
    onScheme(read.scheme);
    onTyped(null);
  };
  const discard = () => {
    setError(null);
    onTyped(null);
  };
  return (
    <div className="space-y-2" data-path="advanced.json">
      <p className="text-osce-caption text-ink-subtle">Custom rows and anything the blocks cannot show are edited here.</p>
      <Textarea
        textareaSize="sm"
        rows={16}
        readOnly={readOnly}
        value={typed ?? JSON.stringify(scheme, null, 2)}
        onChange={(event) => onTyped(event.target.value)}
        className="font-mono"
        aria-label="Scheme as JSON"
        invalid={error !== null}
      />
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {typed !== null && !error ? <p className="text-osce-caption text-osce-warning-text">These JSON edits are not applied yet. Apply them, or discard them, before you save or leave.</p> : null}
      {readOnly ? null : (
        <div className="flex gap-2">
          <AuthoringButton variant="secondary" size="sm" disabled={typed === null} onClick={apply}>
            Apply JSON
          </AuthoringButton>
          <AuthoringButton variant="ghost" size="sm" disabled={typed === null} onClick={discard}>
            Discard edits
          </AuthoringButton>
        </div>
      )}
    </div>
  );
}
