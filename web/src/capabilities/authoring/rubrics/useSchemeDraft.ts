"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAsync } from "@/foundation/hooks";
import {
  editRubricVersion,
  previewRubric,
  type AuthoringScope,
  type RubricPreview,
  type RubricVersion,
} from "@/capabilities/authoring/api";
import { staleRefusal } from "@/capabilities/authoring/api/stale";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { readScheme, type Problem, type Scheme } from "@/capabilities/authoring/rubrics/schemeModel";
import type { Pacing } from "@/capabilities/authoring/rubrics/AdvancedDisclosure";
import {
  emptyMarkingLayout,
  markingLayoutFromVersion,
  markingLayoutToJson,
} from "@/capabilities/authoring/templates/rubricMarkingLayout";

/** How long typing must pause before the draft is sent to be checked. */
const PREVIEW_DELAY_MS = 400;

interface SchemeDraft {
  structure: Scheme;
  edit: (change: (structure: Scheme) => Scheme) => void;
  systemPrompt: string;
  setSystemPrompt: (value: string) => void;
  pacing: Pacing;
  setPacing: (value: Pacing) => void;
  markingLayout: StationStructure;
  setMarkingLayout: (value: StationStructure) => void;
  /** Something differs from what was last saved. */
  dirty: boolean;
  /** The latest preview the backend answered (kept while the next one loads). */
  preview: RubricPreview | null;
  previewError: Error | null;
  /** The backend has not yet seen the latest edit. */
  checking: boolean;
  problems: readonly Problem[];
  /** Problems a publish was refused with, shown until the next edit. */
  setRefusedProblems: (problems: Problem[]) => void;
  save: () => Promise<RubricVersion>;
}

/** Everything a version saves, as one string, so "dirty" is one comparison. */
function snapshotOf(structure: Scheme, systemPrompt: string, pacing: Pacing, markingLayout: StationStructure): string {
  return JSON.stringify([structure, systemPrompt, pacing, markingLayout]);
}

/** An examiner layout with no sections is sent as none: the backend refuses an empty one. */
function layoutForSave(markingLayout: StationStructure) {
  return markingLayout.sections.length > 0 ? markingLayoutToJson(markingLayout) : null;
}

/**
 * One version being edited: its four saved parts, whether they have changed,
 * and the backend's live verdict on the structure.
 *
 * The structure is sent to `POST …/rubrics/preview` once typing pauses, and
 * the answer is both the validation (every problem at its path) and the
 * preview (a sample result). The last answer is kept while the next loads, so
 * problems do not flicker away on every keystroke.
 */
export function useSchemeDraft(
  scope: AuthoringScope,
  rubricId: string,
  version: RubricVersion,
  /** Someone else saved first: reload the version, so the builder starts over on theirs. */
  onStale: () => void,
): SchemeDraft {
  // The revision this draft last read or wrote, so a second save is not mistaken for a stale one.
  const revision = useRef(version.revision);
  const [structure, setStructure] = useState<Scheme>(() => readScheme(version.structure));
  const [systemPrompt, setSystemPrompt] = useState(version.system_prompt ?? "");
  const [pacing, setPacing] = useState<Pacing>(() => ({ ...(version.pacing ?? {}) }));
  const [markingLayout, setMarkingLayout] = useState<StationStructure>(
    () => markingLayoutFromVersion(version.marking_layout) ?? emptyMarkingLayout(),
  );
  const [saved, setSaved] = useState(() => snapshotOf(structure, systemPrompt, pacing, markingLayout));
  const [checked, setChecked] = useState<Scheme>(structure);
  const [refused, setRefused] = useState<Problem[]>([]);

  // Wait for typing to pause before asking the backend about the structure.
  useEffect(() => {
    if (checked === structure) return;
    const timer = window.setTimeout(() => setChecked(structure), PREVIEW_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [structure, checked]);

  const preview = useAsync((signal) => previewRubric(scope, checked as unknown as Record<string, unknown>, signal), [scope.base, checked]);

  const edit = useCallback((change: (current: Scheme) => Scheme) => {
    setStructure(change);
    setRefused([]);
  }, []);

  const current = snapshotOf(structure, systemPrompt, pacing, markingLayout);
  const problems = useMemo<readonly Problem[]>(() => {
    if (refused.length > 0) return refused;
    return preview.data?.problems ?? version.problems ?? [];
  }, [refused, preview.data, version.problems]);

  const save = useCallback(async () => {
    try {
      const updated = await editRubricVersion(scope, rubricId, version.version, {
        system_prompt: systemPrompt,
        structure: structure as unknown as Record<string, unknown>,
        pacing,
        marking_layout: layoutForSave(markingLayout),
        revision: revision.current,
      });
      revision.current = updated.revision;
      setSaved(snapshotOf(structure, systemPrompt, pacing, markingLayout));
      return updated;
    } catch (cause) {
      const stale = staleRefusal(cause, "marking scheme");
      if (!stale) throw cause;
      onStale();
      throw stale;
    }
  }, [scope, rubricId, version.version, systemPrompt, structure, pacing, markingLayout, onStale]);

  return {
    structure,
    edit,
    systemPrompt,
    setSystemPrompt,
    pacing,
    setPacing,
    markingLayout,
    setMarkingLayout,
    dirty: current !== saved,
    preview: preview.data,
    previewError: preview.error,
    checking: preview.loading || checked !== structure,
    problems,
    setRefusedProblems: setRefused,
    save,
  };
}
