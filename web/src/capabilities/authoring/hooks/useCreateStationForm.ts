"use client";

import { useCallback, useState } from "react";
import {
  autogenerateStationDraft,
  createStation,
  publishStationVersion,
  type Station,
  type StationTemplate,
} from "@/capabilities/authoring/api";
import type { AuthoringScope } from "@/capabilities/authoring/api/scope";
import { validateStationContent } from "@/b2b/lib/stations/validateStationContent";
import type { StationStructure } from "@/b2b/types/b2bStationTemplateTypes";
import {
  b2bStationAiPromptSchema,
  zodErrorFirstMessage,
} from "@/b2b/lib/validation";

function resolvePublishedVersion(
  templates: StationTemplate[],
  versionId: string,
): { examCode: string; structure: StationStructure } | null {
  for (const template of templates) {
    const version = template.versions.find((v) => v.id === versionId && v.status === "published");
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
}: {
  scope: AuthoringScope;
  templates: StationTemplate[];
  onCreated: (station: Station) => void;
}) {
  const [mode, setMode] = useState<"manual" | "ai">("manual");
  const [title, setTitle] = useState("");
  const [templateVersionId, setTemplateVersionId] = useState("");
  const [structure, setStructure] = useState<StationStructure | null>(null);
  const [examCode, setExamCode] = useState("");
  const [content, setContent] = useState<Record<string, unknown>>({});
  const [prompt, setPrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [publishNow, setPublishNow] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setMode("manual");
    setTitle("");
    setTemplateVersionId("");
    setStructure(null);
    setExamCode("");
    setContent({});
    setPrompt("");
    setGenerating(false);
    setPublishNow(false);
    setError(null);
  }, []);

  function handleTemplateSelect(versionId: string) {
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
      setError("Could not load template.");
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
  }

  async function handleGenerateDraft() {
    setError(null);
    if (!templateVersionId) {
      setError("Please choose a published template first.");
      return;
    }
    const promptParsed = b2bStationAiPromptSchema.safeParse({ prompt });
    if (!promptParsed.success) {
      setError(zodErrorFirstMessage(promptParsed.error));
      return;
    }
    setGenerating(true);
    try {
      const r = await autogenerateStationDraft(scope, {
        prompt: promptParsed.data.prompt,
        template_version_id: templateVersionId,
      });
      setContent(r.content ?? {});
      if (!title.trim() && r.suggested_title) {
        setTitle(r.suggested_title);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to generate content.");
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
    if (!templateVersionId || !examCode) {
      setError("Please choose a published template.");
      return;
    }
    if (structure) {
      const v = validateStationContent(structure, content);
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
        template_version_id: templateVersionId,
      });
      if (publishNow) {
        await publishStationVersion(scope, created.id, created.version);
      }
      reset();
      onCreated(created);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create station.");
    } finally {
      setSaving(false);
    }
  }

  const busy = saving || generating;

  return {
    mode,
    setMode,
    title,
    setTitle,
    templateVersionId,
    handleTemplateSelect,
    structure,
    content,
    setContent,
    prompt,
    setPrompt,
    generating,
    publishNow,
    setPublishNow,
    error,
    setError,
    busy,
    saving,
    handleGenerateDraft,
    handleCreate,
  };
}
