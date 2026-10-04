"use client";

import { Select, Textarea, FoldSection } from "@/foundation/ui";
import { useEffect, useState } from "react";
import {
  listStationGenerationProfiles,
  type StationGenerationProfileSummary,
} from "@/capabilities/authoring/structure/b2b/lib/api/stationGenerationProfiles";
import { profileKeyForExamCode } from "@/capabilities/authoring/structure/b2b/lib/stations/generationProfileKeys";
import { structureFromGenerationProfileKey } from "@/capabilities/authoring/structure/b2b/lib/stations/stationTemplatePresets";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { inspectorHint, inspectorLabel } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/inspector/MoreOptions";


export function TemplateGenerationPanel({
  value,
  onChange,
  examCode,
  allowCustomSystemPrompt,
  systemPrompt,
  profileGuidesLoading,
  profileGuidesError,
}: {
  value: StationStructure;
  onChange: (next: StationStructure) => void;
  examCode?: string | null;
  /** Org-owned templates may use profileKey custom + systemPromptOverride. */
  allowCustomSystemPrompt?: boolean;
  systemPrompt?: string;
  profileGuidesLoading?: boolean;
  profileGuidesError?: string | null;
}) {
  const [profiles, setProfiles] = useState<StationGenerationProfileSummary[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const profileKey =
    value.generation?.profileKey ?? profileKeyForExamCode(examCode);

  useEffect(() => {
    let cancelled = false;
    void listStationGenerationProfiles()
      .then((items) => {
        if (!cancelled) setProfiles(items);
      })
      .catch(() => {
        if (!cancelled) setLoadError("Could not load exam types for draft writing.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const patchGeneration = (patch: Partial<NonNullable<StationStructure["generation"]>>) => {
    onChange({
      ...value,
      generation: {
        profileKey,
        ...value.generation,
        ...patch,
      },
    });
  };

  const applyExamType = (nextProfileKey: string) => {
    const preset = structureFromGenerationProfileKey(nextProfileKey);
    if (!preset) {
      patchGeneration({ profileKey: nextProfileKey });
      return;
    }
    onChange({
      ...preset,
      generation: {
        ...preset.generation,
        profileKey: nextProfileKey,
        systemPromptAppend: value.generation?.systemPromptAppend,
        systemPromptOverride: value.generation?.systemPromptOverride,
      },
    });
  };

  return (
    <div className="border-b border-osce-border bg-osce-canvas/60 px-5 py-4">
      <p className="text-osce-body font-semibold text-ink-muted">Draft writing with AI</p>
      <p className={inspectorHint}>
        When someone clicks Generate draft on a station from this template, the AI uses the exam
        type below plus built-in guidance for each field. You only need to add extra notes here or
        on individual fields if you want something different.
      </p>
      {loadError ? <p className="mt-2 text-osce-caption text-red-600">{loadError}</p> : null}
      {profileGuidesError ? (
        <p className="mt-2 text-osce-caption text-red-600">{profileGuidesError}</p>
      ) : null}
      <div className="mt-3 max-w-md">
        <label htmlFor="template-generation-panel-exam-type" className={inspectorLabel}>Exam type</label>
        <Select
          id="template-generation-panel-exam-type"
          value={profileKey}
          onChange={(e) => applyExamType(e.target.value)}
        >
          {profiles.length === 0 ? (
            <option value={profileKey}>{profileKey}</option>
          ) : (
            profiles.map((p) => (
              <option key={p.profileKey} value={p.profileKey}>
                {p.label}
              </option>
            ))
          )}
        </Select>
        <p className={`mt-1.5 ${inspectorHint}`}>
          Changing exam type replaces sections and fields below with that exam&apos;s default
          layout. Your optional AI notes above are kept.
        </p>
      </div>
      {profileKey !== "custom" && (systemPrompt?.trim() || profileGuidesLoading) ? (
        <div className="mt-3 max-w-2xl">
          <FoldSection title="Built-in instructions for this exam (read-only)" defaultOpen={false}>
            {profileGuidesLoading ? (
              <p className={inspectorHint}>Loading…</p>
            ) : (
              <Textarea
                readOnly
                value={systemPrompt ?? ""}
                className="min-h-[5rem] resize-y bg-osce-canvas text-ink-muted"
                rows={6}
                aria-label="Built-in exam instructions for Generate draft"
              />
            )}
          </FoldSection>
        </div>
      ) : null}
      <div className="mt-3">
        <label htmlFor="template-generation-panel-extra-notes" className={inspectorLabel}>Extra notes for the AI (optional)</label>
        <Textarea
          id="template-generation-panel-extra-notes"
          value={value.generation?.systemPromptAppend ?? ""}
          onChange={(e) => patchGeneration({ systemPromptAppend: e.target.value })}
          className="min-h-[4rem] resize-y"
          rows={2}
          placeholder="Anything you want the AI to always keep in mind for this template"
        />
      </div>
      {allowCustomSystemPrompt && profileKey === "custom" ? (
        <div className="mt-3">
          <label htmlFor="template-generation-panel-your-own-main-instructions" className={inspectorLabel}>Your own main instructions</label>
          <Textarea
            id="template-generation-panel-your-own-main-instructions"
            value={value.generation?.systemPromptOverride ?? ""}
            onChange={(e) => patchGeneration({ systemPromptOverride: e.target.value })}
            className="min-h-[6rem] resize-y"
            rows={4}
            placeholder="Replaces the usual exam instructions when exam type is Custom"
          />
        </div>
      ) : null}
    </div>
  );
}
