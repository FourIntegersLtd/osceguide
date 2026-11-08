"use client";

import { RequireAuthor } from "@/capabilities/authoring/parts/RequireAuthor";
import { useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { structureFromStartPoint } from "@/capabilities/authoring/structure/b2b/lib/stations/stationTemplatePresets";
import {
  initialStationStartPoint,
  startOptionsForExam,
  STATION_TEMPLATE_START_OPTIONS,
} from "@/capabilities/authoring/structure/b2b/lib/stations/stationTemplateStartOptions";
import type {
  StationStructure,
  StationTemplateStartPoint,
} from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { StructureBuilder } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/StructureBuilder";
import { TemplateStartPanel } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/TemplateLayoutGallery";
import { boardAlert, boardBtn, boardInput, boardLabel, boardPadWide } from "@/foundation/ui/boardKit";
import { AuthoringExamSelect } from "@/capabilities/authoring/parts/AuthoringExamSelect";
import {
  b2bTemplateTitleSchema,
  zodErrorFirstMessage,
} from "@/capabilities/authoring/structure/b2b/lib/validation";
import { useSurface } from "@/capabilities";
import { LayoutBuilderRail } from "@/capabilities/authoring/templates/LayoutBuilderRail";
import { createStationTemplate, publishStationTemplate } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { isThenStation, stationTemplatesListPath } from "@/capabilities/authoring/templates/paths";
import { stationNewPath } from "@/capabilities/authoring/stations/paths";
import { LayoutBuilderPage } from "@/capabilities/authoring/templates/LayoutBuilderPage";
import { wizardSteps } from "@/capabilities/authoring/templates/wizardSteps";

function StationTemplateNewScreenForm() {
  const scope = useAuthoringScope();
  const { orgSlug, hrefFor } = useSurface();
  const router = useRouter();
  const searchParams = useSearchParams();
  const examCode = searchParams.get("exam")?.trim() || null;
  // Opened from station creation: finish by publishing and going back there.
  const thenStation = isThenStation(searchParams.get("then"));
  // Set once the template exists. If publishing then fails, the retry publishes this one
  // instead of creating a second template.
  const createdId = useRef<string | null>(null);
  const listHref = stationTemplatesListPath(hrefFor);
  const orgKey = orgSlug ?? "platform";
  const [step, setStep] = useState<1 | 2>(1);

  return (
    <LayoutBuilderPage
      title="New template"
      subtitle={
        step === 1
          ? "Choose the exam, name the template, pick a starting layout, then save a draft. Only saved (and published) templates appear in the catalogue list."
          : "Step 2 of 2: sections and fields."
      }
      backHref={listHref}
      backLabel="Station templates"
    >
      <CreateStationTemplateWizardBody
        orgKey={orgKey}
        examCode={examCode}
        step={step}
        onStep={setStep}
        onCancel={() => router.push(listHref)}
        saveLabel={thenStation ? "Save and publish" : "Save draft"}
        onSave={async (title, structure, assignedExamCode) => {
          if (!createdId.current) {
            const template = await createStationTemplate(scope, {
              title,
              structure,
              exam_code: assignedExamCode,
            });
            createdId.current = template.id;
          }
          if (!thenStation) {
            router.push(listHref);
            return;
          }
          const version = await publishStationTemplate(scope, createdId.current);
          router.push(stationNewPath(hrefFor, version.id));
        }}
      />
    </LayoutBuilderPage>
  );
}

function CreateStationTemplateWizardBody({
  orgKey,
  examCode,
  step,
  onStep: setStep,
  onCancel,
  saveLabel,
  onSave,
}: {
  orgKey: string;
  examCode: string | null;
  step: 1 | 2;
  onStep: (step: 1 | 2) => void;
  onCancel: () => void;
  saveLabel: string;
  onSave: (title: string, structure: StationStructure, examCode: string) => Promise<void>;
}) {
  const [selectedExamCode, setSelectedExamCode] = useState(examCode ?? "");
  const [startPoint, setStartPoint] = useState<StationTemplateStartPoint>(() =>
    initialStationStartPoint(orgKey, examCode),
  );
  const [title, setTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleExamChange(code: string) {
    setSelectedExamCode(code);
    setStartPoint(initialStationStartPoint(orgKey, code || null));
  }
  const initialStructure = useMemo(
    () => structureFromStartPoint(startPoint),
    [startPoint],
  );
  const layoutOptions = useMemo(
    () => startOptionsForExam(selectedExamCode, STATION_TEMPLATE_START_OPTIONS),
    [selectedExamCode],
  );
  const [structure, setStructure] = useState<StationStructure>(initialStructure);

  const [structureResetKey, setStructureResetKey] = useState({
    initialStructure,
    step,
  });
  if (
    structureResetKey.initialStructure !== initialStructure ||
    structureResetKey.step !== step
  ) {
    setStructureResetKey({ initialStructure, step });
    if (step === 1) setStructure(initialStructure);
  }
  if (!layoutOptions.some((option) => option.id === startPoint)) {
    const fallback = layoutOptions[0]?.id ?? "blank";
    if (fallback !== startPoint) setStartPoint(fallback);
  }

  const current = step === 1 ? "start" : "sections";
  const errorAlert = error ? (
    <p role="alert" className={boardAlert("bad")}>
      {error}
    </p>
  ) : null;

  async function save() {
    setError(null);
    const parsed = b2bTemplateTitleSchema.safeParse(title);
    if (!parsed.success) {
      setError(zodErrorFirstMessage(parsed.error));
      return;
    }
    if (!selectedExamCode.trim()) {
      setError("Please choose an exam.");
      return;
    }
    try {
      setSaving(true);
      await onSave(parsed.data, structure, selectedExamCode.trim());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "We could not save the template. Try again.");
    } finally {
      setSaving(false);
    }
  }

  function next() {
    setError(null);
    if (!selectedExamCode.trim()) {
      setError("Please choose an exam.");
      return;
    }
    if (!title.trim()) {
      setError("Please enter a template title.");
      return;
    }
    setStep(2);
  }

  const rail = (
    <LayoutBuilderRail
      steps={wizardSteps(current, selectedExamCode !== "" && title.trim() !== "")}
      current={current}
      // Only back: the sections need the exam and name from the first screen.
      onSelect={(id) => {
        if (id === "start") setStep(1);
      }}
    />
  );

  if (step === 1) {
    return (
      <div className={`${boardPadWide} !gap-7`}>
        {rail}
        <TemplateStartPanel
          orgSlug={orgKey}
          title={title}
          onTitleChange={setTitle}
          startPoint={startPoint}
          onStartPointChange={setStartPoint}
          options={layoutOptions}
          layoutSectionLabel="Starting layouts"
          examField={
            <div>
              <label htmlFor="station-template-exam" className={boardLabel}>
                Exam
              </label>
              <AuthoringExamSelect
                id="station-template-exam"
                value={selectedExamCode}
                onChange={handleExamChange}
                required
                emptyLabel="Select an exam…"
                className="[&>select]:min-h-11 [&>select]:text-assess-desc"
              />
            </div>
          }
        />
        {errorAlert}
        <div className="flex flex-wrap items-center gap-2.5 pt-2">
          <button type="button" className={boardBtn()} onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className={boardBtn("primary")} onClick={next}>
            Continue
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-7">
      <label className="block">
        <span className={boardLabel}>Title</span>
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          maxLength={200}
          className={boardInput}
          aria-label="Template title"
        />
      </label>
      <StructureBuilder
        value={structure}
        onChange={setStructure}
        examCode={selectedExamCode}
        allowCustomGenerationPrompt
      />
      {errorAlert}
      <div className="flex flex-wrap items-center gap-2.5 pt-2">
        <button type="button" className={boardBtn()} onClick={() => setStep(1)}>
          Back
        </button>
        <button type="button" className={boardBtn()} onClick={onCancel}>
          Cancel
        </button>
        <button type="button" className={boardBtn("primary")} disabled={saving} onClick={save}>
          {saving ? "Saving…" : saveLabel}
        </button>
      </div>
    </div>
  );
}

export function StationTemplateNewScreen() {
  return (
    <RequireAuthor>
      <StationTemplateNewScreenForm />
    </RequireAuthor>
  );
}
