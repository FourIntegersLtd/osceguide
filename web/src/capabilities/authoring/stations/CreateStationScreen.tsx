"use client";

import { RequireAuthor } from "@/capabilities/authoring/parts/RequireAuthor";
import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Alert, Button, getInputClassName, Select, Textarea, FoldSection } from "@/foundation/ui";
import { b2bWizardTabActive, b2bWizardTabInactive } from "@/capabilities/authoring/structure/b2b/theme/b2bUi";
import { useSurface } from "@/capabilities";
import { type Station } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { supportsPromptGeneration } from "@/capabilities/authoring/api/scope";
import { GeneratedDraft, hasDraftContent } from "@/capabilities/authoring/stations/GeneratedDraft";
import { StationDetail } from "@/capabilities/authoring/sections/StationDetail";
import { StationInstanceContentPanel } from "@/capabilities/authoring/sections/StationInstanceContentPanel";
import { useCreateStationChoices } from "@/capabilities/authoring/parts/useCreateStationChoices";
import { PlatformTemplateWizardPageLayout } from "@/capabilities/authoring/templates/PlatformTemplateWizardPageLayout";
import { platformTemplateWizardFooterClass } from "@/capabilities/authoring/templates/wizardFooter";
import { stationTemplateThenStationPath } from "@/capabilities/authoring/templates/paths";
import { stationsListPath } from "@/capabilities/authoring/stations/paths";
import { stationListUrl } from "@/capabilities/authoring/parts/stationListUrl";
import { LoadError } from "@/capabilities/authoring/parts/LoadError";
import { NewStationChooser } from "@/capabilities/authoring/stations/NewStationChooser";
import { showsCreateForm } from "@/capabilities/authoring/stations/stationStart";

function CreateStationScreenForm() {
  const scope = useAuthoringScope();
  // Drafting from a prompt with no template behind it is the catalogue's route;
  // an institution generates against a published template or writes by hand.
  const promptGeneration = supportsPromptGeneration(scope);
  const { hrefFor } = useSurface();
  const router = useRouter();
  const listHref = stationsListPath(hrefFor);
  // Once saved, the draft opens on its steps (draft, check facts, publish), as a new deck does.
  const [created, setCreated] = useState<Station | null>(null);
  const { form, templates, examCatalog, stationSubtypes, choices, published } = useCreateStationChoices({
    scope,
    onCreated: (station) => {
      setCreated(station);
      // Its own address, replacing /new so Back never returns to a blank form.
      router.replace(stationListUrl(listHref, { status: "active", station: station.id }));
    },
  });

  const aiAvailable = promptGeneration || Boolean(form.templateVersionId);
  const aiMode = form.mode === "ai" && aiAvailable;

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
      subtitle="Choose a published template and fill in content manually or with AI. Saving opens the draft so you can publish it."
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
            : "No published templates yet. You can still write a station by choosing its exam below. Choose a published template to generate a draft with AI."}
        </Alert>
      ) : null}

      {examCatalog.error ? <LoadError message={examCatalog.error} onRetry={examCatalog.reload} /> : null}

      {form.error ? <Alert tone="danger">{form.error}</Alert> : null}

      <div className="space-y-6 p-5 sm:p-6">
        <div className="border-b border-border">
          <div className="flex items-center gap-2">
            {(
              [
                { id: "manual" as const, label: "Manual" },
                // Org staff generate only from a published template (autogenerate-draft); the prompt-only route is the platform catalogue's.
                ...(aiAvailable ? [{ id: "ai" as const, label: "Generate with AI" }] : []),
              ] as const
            ).map((t) => {
              const active = (aiMode ? "ai" : "manual") === t.id;
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
              <option value="">No template: write it from a prompt</option>
              {choices.map((choice) => (
                <option key={choice.id} value={choice.id}>
                  {choice.label}
                </option>
              ))}
            </Select>
            <p className="mt-1 text-osce-caption text-ink-muted">
              Only published templates can be used for stations. A station with no template is
              still a real station. It just borrows the exam&apos;s own shape rather than a reusable
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
        </FoldSection>

        {aiMode && (form.structure || (form.examCode && promptGeneration)) ? (
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
                  (!form.templateVersionId && stationSubtypes.length > 0 && !form.stationSubtype) ||
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
              {form.needsTemplateForLayout ? "This exam needs a template" : "Choose a template or an exam"}
            </p>
            <p className="mt-1 text-osce-body text-ink-muted">
              {form.needsTemplateForLayout ? (
                <>
                  This exam has no built-in station layout. Create a station template for this exam
                  here. It is published when you save it, and you come straight back to this station.{" "}
                  <Link href={stationTemplateThenStationPath(hrefFor, form.examCode)} className="font-semibold text-accent underline">
                    Create a station template
                  </Link>
                </>
              ) : "The full station form appears here as soon as you pick a published template, or say which exam this station is for."}
            </p>
          </div>
        )}

      </div>

      <div className={platformTemplateWizardFooterClass}>
        <Button type="button" variant="secondary" onClick={() => router.push(listHref)} disabled={form.saving}>
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

export function CreateStationScreen() {
  // The route's page puts a Suspense above this, which `useSearchParams` needs.
  const showForm = showsCreateForm(useSearchParams(), useAuthoringScope().kind);
  return <RequireAuthor>{showForm ? <CreateStationScreenForm /> : <NewStationChooser />}</RequireAuthor>;
}
