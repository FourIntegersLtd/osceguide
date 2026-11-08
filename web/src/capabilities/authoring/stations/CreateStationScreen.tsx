"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import { generateDraftHeading, generateDraftHelp } from "@/capabilities/authoring/lib/authoringCopy";
import { RequireAuthor } from "@/capabilities/authoring/parts/RequireAuthor";
import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { B2CPageHeader, FoldSection } from "@/foundation/ui";
import { BoardTabBar, boardTabId } from "@/foundation/ui/BoardTabBar";
import { BoardSelect, BoardTextarea } from "@/foundation/ui/BoardFields";
import { boardAlert, boardBtn, boardInput, boardLabel, boardPadWide } from "@/foundation/ui/boardKit";
import { useSurface } from "@/capabilities";
import { type Station } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { supportsPromptGeneration } from "@/capabilities/authoring/api/scope";
import { GeneratedDraft, hasDraftContent } from "@/capabilities/authoring/stations/GeneratedDraft";
import { StationDetail } from "@/capabilities/authoring/sections/StationDetail";
import { StationInstanceContentPanel } from "@/capabilities/authoring/sections/StationInstanceContentPanel";
import { useCreateStationChoices } from "@/capabilities/authoring/parts/useCreateStationChoices";
import { stationTemplateThenStationPath } from "@/capabilities/authoring/templates/paths";
import { stationsListPath } from "@/capabilities/authoring/stations/paths";
import { stationListUrl } from "@/capabilities/authoring/parts/stationListUrl";
import { LoadError } from "@/capabilities/authoring/parts/LoadError";
import { NewStationChooser } from "@/capabilities/authoring/stations/NewStationChooser";
import { showsCreateForm } from "@/capabilities/authoring/stations/stationStart";

import { assessFormStack } from "@/foundation/ui/b2bTokens";

const label = `${boardLabel} !leading-[1.6]`;
const boardHint = "mt-2 text-assess-meta leading-normal text-ink-subtle";
const cardTitle = "text-assess-hero font-semibold leading-snug text-ink";

function CreateStationScreenForm() {
  const scope = useAuthoringScope();
  const words = useAssessWords();
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

  const tabs = [
    { id: "manual" as const, label: "Manual" },
    // Org staff generate only from a published template (autogenerate-draft); the prompt-only route is the platform catalogue's.
    ...(aiAvailable ? [{ id: "ai" as const, label: "Generate with AI" }] : []),
  ];

  return (
    <div className="flex flex-col gap-8 pb-10" data-testid="create-station-page">
      <B2CPageHeader
        board
        action={<span aria-hidden />}
        className="!mb-0 [&_h1]:-mt-1"
        wideSubtitle
        eyebrow="Exams › Stations"
        title="New station"
        subtitle="Choose a published template and fill in content manually or with AI. Saving opens the draft so you can publish it."
        back={{ href: listHref, label: "Stations" }}
      />

      <BoardTabBar
        label="How to start"
        idPrefix="create-station-tab"
        panelId="create-station-panel"
        tabs={tabs}
        value={aiMode ? "ai" : "manual"}
        onChange={(id) => {
          form.setMode(id);
          form.setError(null);
        }}
      />

      {templates.error ? (
        <p role="alert" className={boardAlert("bad")}>{templates.error.message}</p>
      ) : published.length === 0 && !templates.loading ? (
        /*
         * A hint, no longer a wall. There was a version of this screen that
         * offered nothing at all until a template existed, which made a one-off
         * case impossible to write without first authoring a reusable template
         * for it — and `CreateStation` never required one.
         */
        <p role="status" className={boardAlert("info")}>
          {promptGeneration
            ? "No published templates yet. You can still write a station straight from a prompt by choosing its exam below."
            : "No published templates yet. You can still write a station by choosing its exam below. Choose a published template to generate a draft with AI."}
        </p>
      ) : null}

      {examCatalog.error ? <LoadError message={examCatalog.error} onRetry={examCatalog.reload} /> : null}

      {form.error ? <p role="alert" className={boardAlert("bad")}>{form.error}</p> : null}

      <div id="create-station-panel" role="tabpanel" aria-labelledby={boardTabId("create-station-tab", aiMode ? "ai" : "manual")}>
      <FoldSection board title="Station details">
        <div className={assessFormStack}>
        <div>
          <label htmlFor="create-station-screen-station-title" className={label}>
            Station title
          </label>
          <input
            id="create-station-screen-station-title"
            value={form.title}
            onChange={(e) => form.setTitle(e.target.value)}
            className={boardInput}
            placeholder="e.g. Chest pain counselling"
          />
        </div>
        <div>
          <label htmlFor="create-station-screen-template" className={label}>Template</label>
          <BoardSelect
            id="create-station-screen-template"
            value={form.templateVersionId}
            onChange={(e) => form.handleTemplateSelect(e.target.value)}
            disabled={templates.loading}
          >
            <option value="">No template: write it from a prompt</option>
            {choices.map((choice) => (
              <option key={choice.id} value={choice.id}>
                {choice.label}
              </option>
            ))}
          </BoardSelect>
          <p className={boardHint}>
            Only published templates can be used for stations. A station with no template is still a real station.
            It just borrows the exam&apos;s own shape rather than a reusable one.
            {form.templateVersionId ? "" : " An exam of your own has no built-in layout, so choose or create one."}
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
            <label htmlFor="create-station-screen-exam" className={label}>Exam</label>
            <BoardSelect
              id="create-station-screen-exam"
              value={form.examCode}
              onChange={(e) => form.setExamCode(e.target.value)}
            >
              <option value="">Select an exam…</option>
              {examCatalog.exams.map((exam) => (
                <option key={exam.code} value={exam.code}>
                  {exam.name}
                </option>
              ))}
            </BoardSelect>
          </div>
        ) : null}

        {!form.templateVersionId && stationSubtypes.length > 0 ? (
          <div>
            <label htmlFor="create-station-screen-station-type" className={label}>
              Station type
            </label>
            <BoardSelect
              id="create-station-screen-station-type"
              value={form.stationSubtype}
              onChange={(e) => form.setStationSubtype(e.target.value)}
            >
              <option value="">Choose the kind of station…</option>
              {stationSubtypes.map((subtype) => (
                <option key={subtype.key} value={subtype.key}>
                  {subtype.label}
                </option>
              ))}
            </BoardSelect>
            <p className={boardHint}>
              These stations are scored differently, so the prompt is steered by the type rather
              than left to guess.
            </p>
          </div>
        ) : null}
      </div>
      </FoldSection>
      </div>

      {aiMode && (form.structure || (form.examCode && promptGeneration)) ? (
        <FoldSection
          board
          title={generateDraftHeading(words)}
          description={generateDraftHelp(words)}
        >
          <div className="flex flex-col gap-3.5">
            <BoardTextarea
              value={form.prompt}
              onChange={(e) => form.setPrompt(e.target.value)}
              className="min-h-24"
              placeholder="e.g. 72F falls at home, hip pain, shortened externally rotated leg. Candidate to assess and plan management including peri-op considerations."
            />
            <button
              type="button"
              className={`${boardBtn("primary")} self-start`}
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
            </button>
          </div>
        </FoldSection>
      ) : null}

      {form.structure ? (
        <StationInstanceContentPanel
          board
          gap
          structure={form.structure}
          content={form.content}
          onChange={form.setContent}
        />
      ) : hasDraftContent(form.content) ? (
        <GeneratedDraft content={form.content} />
      ) : form.needsTemplateForLayout ? (
        <div className={boardPadWide}>
          <h2 className={cardTitle}>This exam needs a template</h2>
          <p className="m-0 text-assess-meta text-ink-subtle">
            A station needs a layout to write into, and this exam has none. Create one for this exam
            (it is published when you save it) and you come straight back here. Save draft stays
            off until then.
          </p>
          <Link href={stationTemplateThenStationPath(hrefFor, form.examCode)} className={`${boardBtn()} self-start`}>
            Create a layout for this exam
          </Link>
        </div>
      ) : (
        <div className={boardPadWide}>
          <h2 className={cardTitle}>Choose a template or an exam</h2>
          <p className="m-0 text-assess-meta text-ink-subtle">
            The full station form appears here as soon as you pick a published template, or say which exam this station is for.
          </p>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2.5 pt-2">
        <button type="button" className={boardBtn()} onClick={() => router.push(listHref)} disabled={form.saving}>
          Cancel
        </button>
        <button type="button" className={boardBtn("primary")} disabled={!canSave} onClick={() => form.handleCreate()}>
          {form.saving ? "Saving…" : "Save draft"}
        </button>
      </div>
    </div>
  );
}

export function CreateStationScreen() {
  // The route's page puts a Suspense above this, which `useSearchParams` needs.
  const showForm = showsCreateForm(useSearchParams(), useAuthoringScope().kind);
  return <RequireAuthor>{showForm ? <CreateStationScreenForm /> : <NewStationChooser />}</RequireAuthor>;
}
