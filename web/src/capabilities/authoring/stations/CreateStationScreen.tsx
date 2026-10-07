"use client";

import { RequireAuthor } from "@/capabilities/authoring/parts/RequireAuthor";
import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Alert,
  Button,
  getInputClassName,
  Select,
  Textarea,
  FoldSection,
} from "@/foundation/ui";
import {
  b2bWizardTabActive,
  b2bWizardTabInactive,
} from "@/capabilities/authoring/structure/b2b/theme/b2bUi";
import { useSurface } from "@/capabilities";
import {
  listStationTemplates,
  type Station,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { supportsPromptGeneration } from "@/capabilities/authoring/api/scope";
import { useAsync } from "@/foundation/hooks";
import { hasPublishedVersion } from "@/capabilities/authoring/sections/StationsSection";
import { StationDetail } from "@/capabilities/authoring/sections/StationDetail";
import { StationInstanceContentPanel } from "@/capabilities/authoring/sections/StationInstanceContentPanel";
import { useCreateStationForm } from "@/capabilities/authoring/hooks/useCreateStationForm";
import { PlatformTemplateWizardPageLayout } from "@/capabilities/authoring/templates/PlatformTemplateWizardPageLayout";
import { platformTemplateWizardFooterClass } from "@/capabilities/authoring/templates/wizardFooter";
import { stationTemplateNewPath } from "@/capabilities/authoring/templates/paths";
import { stationsListPath } from "@/capabilities/authoring/stations/paths";
import { stationListUrl } from "@/capabilities/authoring/parts/stationListUrl";
import { useAuthoringExamCatalog } from "@/capabilities/authoring/parts/useAuthoringExamCatalog";

function CreateStationScreenForm() {
  const scope = useAuthoringScope();
  // Drafting from a prompt with no template behind it is the catalogue's route;
  // an institution generates against a published template or writes by hand.
  const promptGeneration = supportsPromptGeneration(scope);
  const { hrefFor } = useSurface();
  const router = useRouter();
  const listHref = stationsListPath(hrefFor);

  const templates = useAsync(
    (signal) => listStationTemplates(scope, signal),
    [scope.base],
  );
  const published = useMemo(
    () => (templates.data?.items ?? []).filter(hasPublishedVersion),
    [templates.data],
  );

  // Once saved, the draft opens on its steps (draft, check facts, publish), as a new deck does.
  const [created, setCreated] = useState<Station | null>(null);
  const form = useCreateStationForm({
    scope,
    templates: published,
    onCreated: (station) => {
      setCreated(station);
      // Its own address, replacing /new so Back never returns to a blank form.
      router.replace(
        stationListUrl(listHref, { status: "active", station: station.id }),
      );
    },
  });

  // Which sub-types the template-less exam offers, if any. Sourced from the
  // exam's own settings rather than a hardcoded list, so a new exam that
  // declares `station_subtypes` gets the picker for free.
  const examCatalog = useAuthoringExamCatalog();
  const stationSubtypes = useMemo(
    () =>
      examCatalog.exams.find((exam) => exam.code === form.examCode)?.settings
        ?.station_subtypes ?? [],
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
    !form.needsTemplateForLayout &&
    !form.busy;
  if (created) {
    return (
      <StationDetail
        station={created}
        templates={templates.data?.items ?? []}
        onBack={() => router.push(listHref)}
      />
    );
  }

  return (
    <PlatformTemplateWizardPageLayout
      title="New station"
      subtitle="Choose a published template and fill in content manually or with AI. Saving opens the draft to check its facts and publish."
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
            : "No published templates yet. You can still write a station by choosing its exam below. Generating one from a prompt needs a published template to generate against."}
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

        <FoldSection title="Station details">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="create-station-screen-station-title"
                className="block text-osce-body font-semibold text-ink"
              >
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
              <label
                htmlFor="create-station-screen-template"
                className="block text-osce-body font-semibold text-ink"
              >
                Template
              </label>
              <Select
                id="create-station-screen-template"
                value={form.templateVersionId}
                onChange={(e) => form.handleTemplateSelect(e.target.value)}
                disabled={templates.loading}
                className="mt-1"
              >
                <option value="">No template: write it from a prompt</option>
                {choices.map((choice) => (
                  <option key={choice.id} value={choice.id}>
                    {choice.label}
                  </option>
                ))}
              </Select>
              <p className="mt-1 text-osce-caption text-ink-muted">
                Only published templates can be used for stations. A station
                with no template is still a real station. It just borrows the
                exam&apos;s own shape rather than a reusable one.
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
                <label
                  htmlFor="create-station-screen-exam"
                  className="block text-osce-body font-semibold text-ink"
                >
                  Exam
                </label>
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
                <label
                  htmlFor="create-station-screen-station-type"
                  className="block text-osce-body font-semibold text-ink"
                >
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
                  These stations are scored differently, so the prompt is
                  steered by the type rather than left to guess.
                </p>
              </div>
            ) : null}
          </div>
        </FoldSection>

        {/*
          The AI tab stays selectable for an institution, because with a
          template chosen it genuinely works (`autogenerate-draft`). What it
          cannot do is draft from a prompt alone, so say that instead of
          rendering an empty panel underneath a tab somebody just clicked.
        */}
        {form.mode === "ai" && !form.structure && !promptGeneration ? (
          <Alert tone="info">
            Generating a draft needs a published template to generate against.
            Choose one above, or switch to Manual and write the station
            yourself. A station with no template is still a real station.
          </Alert>
        ) : null}

        {form.mode === "ai" &&
        (form.structure || (form.examCode && promptGeneration)) ? (
          <FoldSection
            title="Generate draft"
            description="Paste a short prompt (a few lines). We’ll auto-fill the template fields below; you can edit anything afterward."
          >
            <Textarea
              value={form.prompt}
              onChange={(e) => form.setPrompt(e.target.value)}
              rows={6}
              placeholder="e.g. 72F falls at home, hip pain, shortened externally rotated leg. Candidate to assess and plan management including peri-op considerations."
            />
            <div className="mt-3 flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="commit"
                disabled={
                  form.generating ||
                  (!form.templateVersionId && !form.examCode) ||
                  (!form.templateVersionId &&
                    stationSubtypes.length > 0 &&
                    !form.stationSubtype) ||
                  !form.prompt.trim() ||
                  form.saving
                }
                onClick={() => form.handleGenerateDraft()}
              >
                {form.generating ? "Generating…" : "Generate draft"}
              </Button>
            </div>
          </FoldSection>
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
              {form.needsTemplateForLayout
                ? "This exam needs a template"
                : "Choose a template or an exam"}
            </p>
            <p className="mt-1 text-osce-body text-ink-muted">
              {form.needsTemplateForLayout ? (
                <>
                  This exam has no built-in station layout. Create a station
                  template for this exam first, publish it from the templates
                  list, then pick it here. The exam is filled in for you.{" "}
                  <Link
                    href={stationTemplateNewPath(hrefFor, form.examCode)}
                    className="font-semibold text-accent underline"
                  >
                    Create a station template
                  </Link>
                </>
              ) : (
                "The full station form appears here as soon as you pick a published template, or say which exam this station is for."
              )}
            </p>
          </div>
        )}
      </div>

      <div className={platformTemplateWizardFooterClass}>
        <Button
          type="button"
          variant="secondary"
          onClick={() => router.push(listHref)}
          disabled={form.saving}
        >
          Cancel
        </Button>
        <Button
          type="button"
          variant="commit"
          disabled={!canSave}
          onClick={() => form.handleCreate()}
        >
          {form.saving ? "Saving…" : "Save draft"}
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

export function CreateStationScreen() {
  return (
    <RequireAuthor>
      <CreateStationScreenForm />
    </RequireAuthor>
  );
}
