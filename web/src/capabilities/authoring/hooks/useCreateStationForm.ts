"use client";

import { useCallback, useState } from "react";
import {
  autogenerateStationDraft,
  createStation,
  generateStation,
  type Station,
  type StationTemplate,
} from "@/capabilities/authoring/api";
import {
  supportsPromptGeneration,
  type AuthoringScope,
} from "@/capabilities/authoring/api/scope";
import { legacyB2cStationStructure } from "@/capabilities/authoring/lib/legacyB2cStationStructure";
import { validateStationContent } from "@/capabilities/authoring/structure/b2b/lib/stations/validateStationContent";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import {
  b2bStationAiPromptSchema,
  zodErrorFirstMessage,
} from "@/capabilities/authoring/structure/b2b/lib/validation";

function resolvePublishedVersion(
  templates: StationTemplate[],
  versionId: string,
): { examCode: string; structure: StationStructure } | null {
  for (const template of templates) {
    const version = template.versions.find(
      (v) => v.id === versionId && v.status === "published",
    );
    if (version) {
      const examCode = template.exam_code?.trim() ?? "";
      return {
        examCode,
        structure: version.structure as StationStructure,
      };
    }
  }
  return null;
}

export function useCreateStationForm({
  scope,
  templates,
  onCreated,
  initial,
}: {
  scope: AuthoringScope;
  templates: StationTemplate[];
  onCreated: (station: Station) => void;
  /** What the chooser already settled, so the form opens on it. */
  initial?: { examCode?: string; mode?: "manual" | "ai" };
}) {
  const [mode, setMode] = useState<"manual" | "ai">(initial?.mode ?? "manual");
  const [title, setTitle] = useState("");
  const [templateVersionId, setTemplateVersionId] = useState("");
  const [structure, setStructure] = useState<StationStructure | null>(null);
  const [examCode, setExamCode] = useState(initial?.examCode ?? "");
  /** Only sent when the chosen exam's settings declare `station_subtypes`. */
  const [stationSubtype, setStationSubtype] = useState("");
  const [content, setContent] = useState<Record<string, unknown>>({});
  const [prompt, setPrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /*
   * The layout the author writes into.
   *
   * A chosen template supplies one. Without a template the station borrows the
   * exam's own shape — the same accordion the retiring b2c admin wrote library
   * stations in — rather than showing nothing at all. Showing nothing is what
   * let "No template" mean "publish an empty station": the content panel was
   * gated on a template, so the fields never appeared, and the create and
   * publish routes check no content.
   *
   * An exam with no built-in layout (an institution's own) still resolves to
   * null, and the screen says so instead of pretending there is a form.
   */
  const effectiveStructure =
    structure ??
    (examCode
      ? legacyB2cStationStructure(examCode, {
          ...content,
          station_type: content.station_type ?? stationSubtype,
        })
      : null);

  const reset = useCallback(() => {
    setMode("manual");
    setTitle("");
    setTemplateVersionId("");
    setStructure(null);
    setExamCode("");
    setStationSubtype("");
    setContent({});
    setPrompt("");
    setGenerating(false);
    setError(null);
  }, []);

  const handleTemplateSelect = useCallback(
    (versionId: string) => {
      setTemplateVersionId(versionId);
      setError(null);
      if (!versionId) {
        setStructure(null);
        setExamCode("");
        setContent({});
        return;
      }
      const resolved = resolvePublishedVersion(templates, versionId);
      if (!resolved) {
        setStructure(null);
        setExamCode("");
        setContent({});
        setError("We could not load the template. Reload the page to try again.");
        return;
      }
      if (!resolved.examCode) {
        setStructure(null);
        setExamCode("");
        setContent({});
        setError("This template has no exam assigned.");
        return;
      }
      setStructure(resolved.structure);
      setExamCode(resolved.examCode);
      setContent({});
    },
    [templates],
  );

  async function handleGenerateDraft() {
    setError(null);
    const promptParsed = b2bStationAiPromptSchema.safeParse({ prompt });
    if (!promptParsed.success) {
      setError(zodErrorFirstMessage(promptParsed.error));
      return;
    }
    /*
     * Two routes to the same box.
     *
     * With a template chosen, generation is bound to that structure and answers
     * a suggested title too. Without one, the platform writes a one-off case
     * from the exam's own shape — the legacy "auto-station" screen — which needs
     * the author to say which exam, because there is no template to read it from.
     */
    if (!templateVersionId && !examCode) {
      setError("Choose a template, or choose the exam the station is for.");
      return;
    }
    /*
     * Refused here rather than by the server. The template-less route is the
     * platform catalogue's (`POST /platform/generate/station` takes
     * PlatformAdmin); an organisation generates through `autogenerate-draft`,
     * which needs a published template to generate against. Without this the
     * button answered a bare Forbidden, which reads as the feature being broken
     * rather than as a thing this workspace does not have. The screen hides the
     * control too — this is the backstop for state that got there another way.
     */
    if (!templateVersionId && !supportsPromptGeneration(scope)) {
      setError(
        "Drafting from a prompt alone is the platform catalogue's. Choose a published template to generate against, or write the station yourself below.",
      );
      return;
    }
    setGenerating(true);
    try {
      if (templateVersionId) {
        const r = await autogenerateStationDraft(scope, {
          prompt: promptParsed.data.prompt,
          template_version_id: templateVersionId,
        });
        setContent(r.content ?? {});
        if (!title.trim() && r.suggested_title) {
          setTitle(r.suggested_title);
        }
      } else {
        const r = await generateStation({
          prompt: promptParsed.data.prompt,
          examCode,
          stationSubtype: stationSubtype || null,
        });
        setContent(r.content ?? {});
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "We could not write the draft. Check your connection and try again.");
    } finally {
      setGenerating(false);
    }
  }

  async function handleCreate() {
    setError(null);
    if (!title.trim()) {
      setError("Please enter a station title.");
      return;
    }
    if (!examCode) {
      setError("Choose a template, or choose the exam the station is for.");
      return;
    }
    /*
     * Validated against whichever structure the author was actually shown.
     *
     * A template-less station borrows the exam's own layout, so it has one too
     * — and it has to be checked here, because the create and publish routes
     * validate no content at all. Without this a "No template" station could
     * be published into circuits with no brief, no patient and no marking
     * scheme in it, which is what was happening.
     */
    if (effectiveStructure) {
      const v = validateStationContent(effectiveStructure, content);
      if (!v.ok) {
        setError(v.errors[0] ?? "Please fill all required fields.");
        return;
      }
    }
    setSaving(true);
    try {
      const created = await createStation(scope, {
        title: title.trim(),
        exam_code: examCode,
        content,
        template_version_id: templateVersionId || null,
      });
      reset();
      onCreated(created);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "We could not create the station. Check your connection and try again.");
    } finally {
      setSaving(false);
    }
  }

  const busy = saving || generating;

  return {
    mode,
    setMode,
    examCode,
    setExamCode,
    stationSubtype,
    setStationSubtype,
    title,
    setTitle,
    templateVersionId,
    handleTemplateSelect,
    structure: effectiveStructure,
    /** True when the exam has no built-in layout and no template was chosen. */
    needsTemplateForLayout:
      !structure && Boolean(examCode) && effectiveStructure === null,
    content,
    setContent,
    prompt,
    setPrompt,
    generating,
    error,
    setError,
    busy,
    saving,
    handleGenerateDraft,
    handleCreate,
  };
}
