"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { Alert, Button, Checkbox, getInputClassName, Select, Textarea } from "@/foundation/ui";
import { b2bWizardTabActive, b2bWizardTabInactive } from "@/capabilities/authoring/structure/b2b/theme/b2bUi";
import { useSurface } from "@/capabilities";
import { listStationTemplates } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { supportsPromptGeneration } from "@/capabilities/authoring/api/scope";
import { useAsync } from "@/foundation/hooks";
import { hasPublishedVersion } from "@/capabilities/authoring/sections/StationsSection";
import { StationInstanceContentPanel } from "@/capabilities/authoring/sections/StationInstanceContentPanel";
import { useCreateStationForm } from "@/capabilities/authoring/hooks/useCreateStationForm";
import { PlatformTemplateWizardPageLayout } from "@/capabilities/authoring/templates/PlatformTemplateWizardPageLayout";
import { platformTemplateWizardFooterClass } from "@/capabilities/authoring/templates/PlatformTemplateWizardStepStrip";
import { stationsListPath } from "@/capabilities/authoring/stations/paths";
import { useAuthoringExamCatalog } from "@/capabilities/authoring/parts/useAuthoringExamCatalog";

export function CreateStationScreen() {
  const scope = useAuthoringScope();
  // Drafting from a prompt with no template behind it is the catalogue's route;
  // an institution generates against a published template or writes by hand.
  const promptGeneration = supportsPromptGeneration(scope);
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

  // Which sub-types the template-less exam offers, if any. Sourced from the
  // exam's own settings rather than a hardcoded list, so a new exam that
  // declares `station_subtypes` gets the picker for free.
  const examCatalog = useAuthoringExamCatalog();
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
          .map((v) => ({
            id: v.id,
            label: `${t.title} (v${v.version})`,
          })),
      ),
    [published],
  );

  const canSave =
    Boolean(form.title.trim()) &&
    Boolean(form.examCode || form.templateVersionId) &&
    !form.busy;
  // A template form is the draft. Generated text with no template is the draft
  // only once it is on screen — publishing before that shipped unseen content.
  const publishAllowed = Boolean(form.structure) || hasDraftContent(form.content);

  return (
    <PlatformTemplateWizardPageLayout
      title="New station"
      subtitle="Choose a published template, fill in content manually or with AI, then save as draft or publish."
      backHref={listHref}
      backLabel="Stations"
    >
      {templates.error ? (
        <Alert tone="danger">{templates.error.message}</Alert>
      ) : published.length === 0 && !templates.loading ? (
        /*
         * A hint, no longer a wall. There was a version of this screen that
         * offered nothing at all until a template existed, which made a one-off
         * case impossible to write without first authoring a reusable template
         * for it — and `CreateStation` never required one.
         */
        <Alert tone="info">
          {promptGeneration
            ? "No published templates yet. You can still write a station straight from a prompt by choosing its exam below."
            : "No published templates yet. You can still write a station by choosing its exam below — generating one from a prompt needs a published template to generate against."}
        </Alert>
      ) : null}

      {form.error ? <Alert tone="danger">{form.error}</Alert> : null}

      <div className="space-y-6 p-5 sm:p-6">
        <div className="border-b border-border">
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
            <label htmlFor="create-station-screen-station-title" className="block text-osce-body font-semibold text-ink">
              Station title
            </label>
            <input
              id="create-station-screen-station-title"
              value={form.title}
              onChange={(e) => form.setTitle(e.target.value)}
              className={`mt-1 ${getInputClassName()}`}
              placeholder="e.g. Chest pain counselling"
            />
          </div>
          <div>
            <label htmlFor="create-station-screen-template" className="block text-osce-body font-semibold text-ink">Template</label>
            <Select
              id="create-station-screen-template"
              value={form.templateVersionId}
              onChange={(e) => form.handleTemplateSelect(e.target.value)}
              disabled={templates.loading}
              className="mt-1"
            >
              <option value="">No template — write it from a prompt</option>
              {choices.map((choice) => (
                <option key={choice.id} value={choice.id}>
                  {choice.label}
                </option>
              ))}
            </Select>
            <p className="mt-1 text-osce-caption text-ink-muted">
              Only published templates can be used for stations. A station with no template is
              still a real station — it just borrows the exam&apos;s own shape rather than a reusable
              one.
            </p>
          </div>

          {/*
            Which exam, when the template is not saying. A chosen template already
            carries its exam, so this asks only in the template-less case — and
            `ortho` is the one exam whose generation route takes a further
            discriminator, because an orthopaedic station is a type as much as a
            topic.
          */}
          {!form.templateVersionId ? (
            <div>
              <label htmlFor="create-station-screen-exam" className="block text-osce-body font-semibold text-ink">Exam</label>
              <Select
                id="create-station-screen-exam"
                value={form.examCode}
                onChange={(e) => form.setExamCode(e.target.value)}
                className="mt-1"
              >
                <option value="">Select an exam…</option>
                {examCatalog.exams.map((exam) => (
                  <option key={exam.code} value={exam.code}>
                    {exam.name}
                  </option>
                ))}
              </Select>
            </div>
          ) : null}

          {!form.templateVersionId && stationSubtypes.length > 0 ? (
            <div>
              <label htmlFor="create-station-screen-station-type" className="block text-osce-body font-semibold text-ink">
                Station type
              </label>
              <Select
                id="create-station-screen-station-type"
                value={form.stationSubtype}
                onChange={(e) => form.setStationSubtype(e.target.value)}
                className="mt-1"
              >
                <option value="">Choose the kind of station…</option>
                {stationSubtypes.map((subtype) => (
                  <option key={subtype.key} value={subtype.key}>
                    {subtype.label}
                  </option>
                ))}
              </Select>
              <p className="mt-1 text-osce-caption text-ink-muted">
                These stations are scored differently, so the prompt is steered by the type rather
                than left to guess.
              </p>
            </div>
          ) : null}
        </div>

        {/*
          The AI tab stays selectable for an institution, because with a
          template chosen it genuinely works (`autogenerate-draft`). What it
          cannot do is draft from a prompt alone, so say that instead of
          rendering an empty panel underneath a tab somebody just clicked.
        */}
        {form.mode === "ai" && !form.structure && !promptGeneration ? (
          <Alert tone="info">
            Generating a draft needs a published template to generate against. Choose one above, or
            switch to Manual and write the station yourself — a station with no template is still a
            real station.
          </Alert>
        ) : null}

        {form.mode === "ai" && (form.structure || (form.examCode && promptGeneration)) ? (
          <div className="rounded-osce-lg border border-border bg-white p-4">
            <p className="text-osce-body font-semibold text-ink">Generate draft</p>
            <p className="mt-1 text-osce-body text-ink-muted">
              Paste a short prompt (a few lines). We’ll auto-fill the template fields below; you can
              edit anything afterward.
            </p>
            <Textarea
              value={form.prompt}
              onChange={(e) => form.setPrompt(e.target.value)}
              rows={6}
              className="mt-3"
              placeholder="e.g. 72F falls at home, hip pain, shortened externally rotated leg. Candidate to assess and plan management including peri-op considerations."
            />
            <div className="mt-3 flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="commit"
                disabled={
                  form.generating ||
                  (!form.templateVersionId && !form.examCode) ||
                  (!form.templateVersionId && stationSubtypes.length > 0 && !form.stationSubtype) ||
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
        ) : hasDraftContent(form.content) ? (
          <GeneratedDraft content={form.content} />
        ) : (
          <div className="rounded-osce-lg border border-dashed border-border bg-surface-raised/40 px-4 py-8 text-center">
            <p className="text-osce-body font-medium text-ink">
              {form.needsTemplateForLayout ? "This exam needs a template" : "Choose a template or an exam"}
            </p>
            <p className="mt-1 text-osce-body text-ink-muted">
              {form.needsTemplateForLayout
                ? "This exam has no built-in station layout, so pick a published template to write against."
                : "The full station form appears here as soon as you pick a published template, or say which exam this station is for."}
            </p>
          </div>
        )}

        <Checkbox
          checked={publishAllowed && form.publishNow}
          disabled={!publishAllowed || form.generating}
          onChange={(e) => form.setPublishNow(e.target.checked)}
          label="Publish immediately (makes station selectable in circuits)"
          className="items-center"
        />
        {!publishAllowed ? (
          <p className="text-osce-meta text-ink-muted">
            Generate a draft, or pick a template, before publishing. The text has to be on screen first.
          </p>
        ) : null}
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

function hasDraftContent(content: Record<string, unknown>): boolean {
  return Object.keys(content).length > 0;
}

function GeneratedDraft({ content }: { content: Record<string, unknown> }) {
  return (
    <div className="rounded-osce-lg border border-border bg-white p-4">
      <p className="text-osce-body font-semibold text-ink">Generated draft</p>
      <p className="mt-1 text-osce-body text-ink-muted">
        Read this before you publish. It is not live until you save.
      </p>
      <dl className="mt-4 space-y-3">
        {Object.entries(content).map(([key, value]) => (
          <div key={key}>
            <dt className="text-osce-meta font-medium text-ink-muted">{key}</dt>
            <dd className="mt-1 whitespace-pre-wrap text-osce-body text-ink">
              {typeof value === "string" || typeof value === "number"
                ? String(value)
                : JSON.stringify(value, null, 2)}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
