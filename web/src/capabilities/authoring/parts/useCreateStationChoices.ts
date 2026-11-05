"use client";

import { useEffect, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { listStationTemplates, type Station } from "@/capabilities/authoring/api";
import type { AuthoringScope } from "@/capabilities/authoring/api/scope";
import { useCreateStationForm } from "@/capabilities/authoring/hooks/useCreateStationForm";
import { useAuthoringExamCatalog } from "@/capabilities/authoring/parts/useAuthoringExamCatalog";
import { hasPublishedVersion } from "@/capabilities/authoring/sections/StationsSection";
import { useAsync } from "@/foundation/hooks";

/**
 * What the create-station screen lets the author choose from: published
 * templates, the exam catalogue and the exam's station types, plus the form
 * that holds the choice. Arriving with `?templateVersion=` (back from the
 * template wizard) chooses that template once it has loaded.
 */
export function useCreateStationChoices({
  scope,
  onCreated,
}: {
  scope: AuthoringScope;
  onCreated: (station: Station) => void;
}) {
  const params = useSearchParams();
  const preselected = params.get("templateVersion");
  const templates = useAsync((signal) => listStationTemplates(scope, signal), [scope.base]);
  const published = useMemo(
    () => (templates.data?.items ?? []).filter(hasPublishedVersion),
    [templates.data],
  );
  const form = useCreateStationForm({
    scope,
    templates: published,
    onCreated,
    // From the chooser; a named template brings its own exam.
    initial: {
      examCode: preselected ? undefined : (params.get("exam") ?? undefined),
      mode: params.get("start") === "ai" ? "ai" : undefined,
    },
  });

  const examCatalog = useAuthoringExamCatalog();
  // Sourced from the exam's own settings, so a new exam that declares
  // `station_subtypes` gets the picker for free.
  const stationSubtypes = useMemo(
    () =>
      examCatalog.exams.find((exam) => exam.code === form.examCode)?.settings?.station_subtypes ??
      [],
    [examCatalog.exams, form.examCode],
  );

  const choices = useMemo(
    () =>
      published.flatMap((t) =>
        t.versions
          .filter((v) => v.status === "published")
          .map((v) => ({ id: v.id, label: `${t.title} (v${v.version})` })),
      ),
    [published],
  );

  const { templateVersionId, handleTemplateSelect } = form;
  useEffect(() => {
    if (preselected && !templateVersionId && choices.some((c) => c.id === preselected)) {
      handleTemplateSelect(preselected);
    }
  }, [preselected, templateVersionId, choices, handleTemplateSelect]);

  return { form, templates, examCatalog, stationSubtypes, choices, published };
}
