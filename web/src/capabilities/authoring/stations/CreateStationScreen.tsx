"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { Alert, Button, getInputClassName } from "@/foundation/ui";
import { b2bWizardTabActive, b2bWizardTabInactive } from "@/b2b/theme/b2bUi";
import { useSurface } from "@/capabilities";
import { listStationTemplates } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAsync } from "@/foundation/hooks";
import { hasPublishedVersion } from "@/capabilities/authoring/sections/StationsSection";
import { StationInstanceContentPanel } from "@/capabilities/authoring/sections/StationInstanceContentPanel";
import { useCreateStationForm } from "@/capabilities/authoring/hooks/useCreateStationForm";
import { PlatformTemplateWizardPageLayout } from "@/capabilities/authoring/templates/PlatformTemplateWizardPageLayout";
import { platformTemplateWizardFooterClass } from "@/capabilities/authoring/templates/PlatformTemplateWizardStepStrip";
import { stationsListPath } from "@/capabilities/authoring/stations/paths";

export function CreateStationScreen() {
  const scope = useAuthoringScope();
  const { hrefFor } = useSurface();
  const router = useRouter();
  const listHref = stationsListPath(hrefFor);

  const templates = useAsync((signal) => listStationTemplates(scope, signal), [scope.base]);
  const published = useMemo(
    () => (templates.data?.items ?? []).filter(hasPublishedVersion),
    [templates.data],
  );

  const form = useCreateStationForm({
    scope,
    templates: published,
    onCreated: () => {
      router.push(listHref);
      router.refresh();
    },
  });

  const choices = useMemo(
    () =>
      published.flatMap((t) =>
        t.versions
          .filter((v) => v.status === "published")
          .map((v) => ({
            id: v.id,
            label: `${t.title} (v${v.version})`,
          })),
      ),
    [published],
  );

  const canSave =
    Boolean(form.title.trim()) &&
    Boolean(form.templateVersionId) &&
    Boolean(form.structure) &&
    !form.busy;

  return (
    <PlatformTemplateWizardPageLayout
      eyebrow="Station"
      title="New station"
      subtitle="Choose a published template, fill in content manually or with AI, then save as draft or publish."
      backHref={listHref}
      backLabel="Stations"
    >
      {templates.error ? (
        <Alert tone="danger">{templates.error.message}</Alert>
      ) : published.length === 0 && !templates.loading ? (
        <Alert tone="warning">
          Publish a station template first, then you can create stations from it.
        </Alert>
      ) : null}

      {form.error ? <Alert tone="danger">{form.error}</Alert> : null}

      <div className="space-y-6 p-5 sm:p-6">
        <div className="border-b border-b2b-border">
          <div className="flex items-center gap-2">
            {(
              [
                { id: "manual" as const, label: "Manual" },
                { id: "ai" as const, label: "Generate with AI" },
              ] as const
            ).map((t) => {
              const active = form.mode === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => {
                    form.setMode(t.id);
                    form.setError(null);
                  }}
                  className={[
                    "flex items-center gap-2 py-2 font-medium whitespace-nowrap transition-all",
                    active ? b2bWizardTabActive : b2bWizardTabInactive,
                  ].join(" ")}
                  aria-current={active ? "page" : undefined}
                >
                  {t.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-osce-body font-semibold text-b2b-headline">
              Station title
            </label>
            <input
              value={form.title}
              onChange={(e) => form.setTitle(e.target.value)}
              className={`mt-1 ${getInputClassName()}`}
              placeholder="e.g. Chest pain counselling"
            />
          </div>
          <div>
            <label className="block text-osce-body font-semibold text-b2b-headline">Template</label>
            <select
              value={form.templateVersionId}
              onChange={(e) => form.handleTemplateSelect(e.target.value)}
              disabled={templates.loading}
              className="mt-1 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline disabled:opacity-60"
            >
              <option value="">Select a template…</option>
              {choices.map((choice) => (
                <option key={choice.id} value={choice.id}>
                  {choice.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-osce-caption text-b2b-mid">
              Only published templates can be used for stations.
            </p>
          </div>
        </div>

        {form.mode === "ai" && form.structure ? (
          <div className="rounded-lg border border-b2b-border bg-white p-4">
            <p className="text-osce-body font-semibold text-b2b-headline">Generate draft</p>
            <p className="mt-1 text-osce-body text-b2b-mid">
              Paste a short prompt (a few lines). We’ll auto-fill the template fields below; you can
              edit anything afterward.
            </p>
            <textarea
              value={form.prompt}
              onChange={(e) => form.setPrompt(e.target.value)}
              rows={6}
              className="mt-3 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline"
              placeholder="e.g. 72F falls at home, hip pain, shortened externally rotated leg. Candidate to assess and plan management including peri-op considerations."
            />
            <div className="mt-3 flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="commit"
                disabled={
                  form.generating ||
                  !form.templateVersionId ||
                  !form.prompt.trim() ||
                  form.saving
                }
                onClick={() => void form.handleGenerateDraft()}
              >
                {form.generating ? "Generating…" : "Generate draft"}
              </Button>
            </div>
          </div>
        ) : null}

        {form.structure ? (
          <StationInstanceContentPanel
            structure={form.structure}
            content={form.content}
            onChange={form.setContent}
          />
        ) : (
          <div className="rounded-lg border border-dashed border-b2b-border bg-b2b-cream/40 px-4 py-8 text-center">
            <p className="text-osce-body font-medium text-b2b-headline">Select a template</p>
            <p className="mt-1 text-osce-body text-b2b-mid">
              The full station form (collapsible sections per template) appears here as soon as you
              pick a published template.
            </p>
          </div>
        )}

        <label className="flex cursor-pointer items-center gap-2 text-osce-body text-b2b-graphite">
          <input
            type="checkbox"
            checked={form.publishNow}
            onChange={(e) => form.setPublishNow(e.target.checked)}
            className="h-4 w-4 rounded border-b2b-border text-b2b-accent"
          />
          Publish immediately (makes station selectable in circuits)
        </label>
      </div>

      <div className={platformTemplateWizardFooterClass}>
        <Button type="button" variant="secondary" onClick={() => router.push(listHref)} disabled={form.saving}>
          Cancel
        </Button>
        <Button
          type="button"
          variant="commit"
          disabled={!canSave}
          onClick={() => void form.handleCreate()}
        >
          {form.saving
            ? form.publishNow
              ? "Creating…"
              : "Saving…"
            : form.publishNow
              ? "Create and publish"
              : "Save as draft"}
        </Button>
      </div>
    </PlatformTemplateWizardPageLayout>
  );
}
