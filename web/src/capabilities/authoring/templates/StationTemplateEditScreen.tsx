"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { StructureBuilder } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/StructureBuilder";
import { Alert } from "@/foundation/ui";
import { Button } from "@/foundation/ui";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { useSurface } from "@/capabilities";
import {
  editStationTemplateVersion,
  listStationTemplates,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAsync } from "@/foundation/hooks";
import { stationTemplatesListPath } from "@/capabilities/authoring/templates/paths";
import { PlatformTemplateWizardPageLayout } from "@/capabilities/authoring/templates/PlatformTemplateWizardPageLayout";
import { platformTemplateWizardFooterEndClass } from "@/capabilities/authoring/templates/PlatformTemplateWizardStepStrip";
import { b2bInputBase } from "@/foundation/ui/b2bTokens";

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
  const missing = !loading && !match;

  return (
    <PlatformTemplateWizardPageLayout
      title={match?.title || "Edit draft"}
      subtitle={`Version ${version}. Published versions cannot be edited — cut a new draft from the list first.`}
      backHref={listHref}
      backLabel="Station templates"
    >
      {loading ? (
        <p className="px-5 py-8 text-osce-body text-ink-muted">Loading template…</p>
      ) : missing ? (
        <p className="px-5 py-8 text-osce-body text-ink-muted">
          Template not found. It may have been removed.
        </p>
      ) : structure ? (
        <>
          <div className="px-5 py-6 sm:px-6">
            <label className="mb-5 block">
              <span className="mb-1.5 block text-osce-meta font-medium text-ink-muted">Title</span>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                disabled={match?.status !== "draft"}
                maxLength={200}
                className={b2bInputBase}
                aria-label="Template title"
              />
            </label>
            <StructureBuilder value={structure} onChange={setStructure} flatChrome allowCustomGenerationPrompt />
            {error ? (
              <Alert tone="danger" className="mt-4">
                {error}
              </Alert>
            ) : null}
          </div>
          <div className={platformTemplateWizardFooterEndClass}>
            <Button variant="secondary" onClick={() => router.push(listHref)}>
              Cancel
            </Button>
            <Button
              variant="commit"
              disabled={saving || match?.status !== "draft"}
              onClick={async () => {
                setError(null);
                if (match?.status !== "draft") {
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
            </Button>
          </div>
        </>
      ) : null}
    </PlatformTemplateWizardPageLayout>
  );
}
