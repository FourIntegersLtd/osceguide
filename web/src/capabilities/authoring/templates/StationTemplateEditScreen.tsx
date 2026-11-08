"use client";

import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { StructureBuilder } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/StructureBuilder";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { useSurface } from "@/capabilities";
import {
  editStationTemplateVersion,
  listStationTemplates,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { stationTemplatesListPath } from "@/capabilities/authoring/templates/paths";
import { LayoutBuilderPage } from "@/capabilities/authoring/templates/LayoutBuilderPage";
import { boardAlert, boardBtn, boardInput, boardLabel } from "@/foundation/ui/boardKit";

export function StationTemplateEditScreen({
  templateId,
  version,
}: {
  templateId: string;
  version: number;
}) {
  const scope = useAuthoringScope();
  const { hrefFor } = useSurface();
  const router = useRouter();
  const listHref = stationTemplatesListPath(hrefFor);
  const templates = useAsync((signal) => listStationTemplates(scope, signal), [scope.base]);

  const match = useMemo(() => {
    const template = templates.data?.items.find((row) => row.id === templateId);
    const row = template?.versions?.find((v) => v.version === version);
    if (!template || !row) return null;
    const structure = row.structure as StationStructure;
    if (!structure?.sections) return null;
    return { title: template.title, structure, status: row.status };
  }, [templates.data, templateId, version]);

  const editable = useCanAuthor() && match?.status === "draft";
  const [structure, setStructure] = useState<StationStructure | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!match) return;
    setStructure(match.structure);
    setTitle(match.title);
  }, [match]);

  const loading = templates.loading && !templates.data;
  const failed = !loading && templates.error !== null;
  const missing = !loading && !failed && !match;

  return (
    <LayoutBuilderPage
      title={match?.title || "Edit draft"}
      subtitle={
        match && match.status !== "draft"
          ? `Version ${version} is ${match.status}, so it is read only. Make a new draft from the list to change it.`
          : `Version ${version}. Published versions cannot be edited. Make a new draft from the list first.`
      }
      backHref={listHref}
      backLabel="Station templates"
    >
      {loading ? (
        <p className="text-assess-desc text-ink-muted">Loading template…</p>
      ) : failed ? (
        <div className="flex flex-col items-start gap-3">
          <p role="alert" className={`${boardAlert("bad")} self-stretch`}>
            {templates.error ? errorMessage(templates.error) : null}
          </p>
          <button type="button" className={boardBtn()} onClick={templates.reload}>
            Try again
          </button>
        </div>
      ) : missing ? (
        <p className="text-assess-desc text-ink-muted">Template not found. It may have been removed.</p>
      ) : structure ? (
        <>
          <label className="block">
            <span className={boardLabel}>Title</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              disabled={!editable}
              maxLength={200}
              className={boardInput}
              aria-label="Template title"
            />
          </label>
          <StructureBuilder key={version} value={structure} onChange={setStructure} allowCustomGenerationPrompt readOnly={!editable} />
          {error ? (
            <p role="alert" className={boardAlert("bad")}>
              {error}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-2.5">
            <button type="button" className={boardBtn()} onClick={() => router.push(listHref)}>
              {editable ? "Cancel" : "Back"}
            </button>
            <button
              type="button"
              className={`${boardBtn("primary")}${editable ? "" : " hidden"}`}
              disabled={saving || !editable}
              onClick={async () => {
                setError(null);
                if (!editable) {
                  setError("Only a draft version can be edited.");
                  return;
                }
                const nextTitle = title.trim();
                if (!nextTitle) {
                  setError("Enter a title.");
                  return;
                }
                try {
                  setSaving(true);
                  await editStationTemplateVersion(scope, templateId, version, structure, nextTitle);
                  router.push(listHref);
                } catch (e: unknown) {
                  setError(e instanceof Error ? e.message : "Failed to save draft.");
                } finally {
                  setSaving(false);
                }
              }}
            >
              {saving ? "Saving…" : "Save draft"}
            </button>
          </div>
        </>
      ) : null}
    </LayoutBuilderPage>
  );
}
