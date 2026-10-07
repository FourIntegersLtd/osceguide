"use client";

import { RequireAuthor } from "@/capabilities/authoring/parts/RequireAuthor";
import { useMemo, useState } from "react";
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
import { Button, getInputClassName, StepRail } from "@/foundation/ui";
import { AuthoringExamSelect } from "@/capabilities/authoring/parts/AuthoringExamSelect";
import {
  b2bTemplateTitleSchema,
  zodErrorFirstMessage,
} from "@/capabilities/authoring/structure/b2b/lib/validation";
import { useSurface } from "@/capabilities";
import { createStationTemplate } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { stationTemplatesListPath } from "@/capabilities/authoring/templates/paths";
import { PlatformTemplateWizardPageLayout } from "@/capabilities/authoring/templates/PlatformTemplateWizardPageLayout";
import { platformTemplateWizardFooterClass } from "@/capabilities/authoring/templates/wizardFooter";
import { wizardSteps } from "@/capabilities/authoring/templates/wizardSteps";

function StationTemplateNewScreenForm() {
  const scope = useAuthoringScope();
  const { orgSlug, hrefFor } = useSurface();
  const router = useRouter();
  const searchParams = useSearchParams();
  const examCode = searchParams.get("exam")?.trim() || null;
  const listHref = stationTemplatesListPath(hrefFor);
  const orgKey = orgSlug ?? "platform";

  return (
    <PlatformTemplateWizardPageLayout
      title="New template"
      subtitle="Choose the exam, name the template, pick a starting layout, then save a draft. Only saved (and published) templates appear in the catalogue list."
      backHref={listHref}
      backLabel="Station templates"
    >
      <CreateStationTemplateWizardBody
        orgKey={orgKey}
        examCode={examCode}
        onCancel={() => router.push(listHref)}
        onCreated={() => router.push(listHref)}
        onSave={async (title, structure, assignedExamCode) => {
          await createStationTemplate(scope, {
            title,
            structure,
            exam_code: assignedExamCode,
          });
        }}
      />
    </PlatformTemplateWizardPageLayout>
  );
}

function CreateStationTemplateWizardBody({
  orgKey,
  examCode,
  onCancel,
  onCreated,
  onSave,
}: {
  orgKey: string;
  examCode: string | null;
  onCancel: () => void;
  onCreated: () => void;
  onSave: (
    title: string,
    structure: StationStructure,
    examCode: string,
  ) => Promise<void>;
}) {
  const [step, setStep] = useState<1 | 2>(1);
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
  const [structure, setStructure] =
    useState<StationStructure>(initialStructure);

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

  return (
    <>
      <div className="px-5 py-3 sm:px-6">
        <StepRail
          steps={wizardSteps(
            current,
            selectedExamCode !== "" && title.trim() !== "",
          )}
          current={current}
          // Only back: the sections need the exam and name from the first screen.
          onSelect={(id) => {
            if (id === "start") setStep(1);
          }}
        />
      </div>
      <div className="px-5 py-6 sm:px-6">
        {step === 1 ? (
          <TemplateStartPanel
            orgSlug={orgKey}
            title={title}
            onTitleChange={setTitle}
            startPoint={startPoint}
            onStartPointChange={setStartPoint}
            options={layoutOptions}
            layoutSectionLabel="Starting layouts"
            examField={
              <div className="space-y-1">
                <label
                  htmlFor="station-template-exam"
                  className="text-osce-caption font-medium text-ink-muted"
                >
                  Exam
                </label>
                <AuthoringExamSelect
                  id="station-template-exam"
                  value={selectedExamCode}
                  onChange={handleExamChange}
                  required
                  emptyLabel="Select an exam…"
                  className={`w-full ${getInputClassName()}`}
                />
              </div>
            }
          />
        ) : (
          <StructureBuilder
            value={structure}
            onChange={setStructure}
            title={title}
            onTitleChange={setTitle}
            examCode={selectedExamCode}
            allowCustomGenerationPrompt
          />
        )}
        {error ? (
          <div className="mt-4 rounded-osce-md border border-osce-danger-border bg-osce-danger-bg px-3 py-2 text-osce-body text-osce-danger-text">
            {error}
          </div>
        ) : null}
      </div>
      <div className={platformTemplateWizardFooterClass}>
        {step === 2 ? (
          <Button variant="secondary" onClick={() => setStep(1)}>
            Back
          </Button>
        ) : (
          <span />
        )}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          {step === 1 ? (
            <Button
              variant="commit"
              onClick={() => {
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
              }}
            >
              Continue
            </Button>
          ) : (
            <Button
              variant="commit"
              disabled={saving}
              onClick={async () => {
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
                  onCreated();
                } catch (e: unknown) {
                  setError(
                    e instanceof Error
                      ? e.message
                      : "Failed to create template.",
                  );
                } finally {
                  setSaving(false);
                }
              }}
            >
              {saving ? "Saving…" : "Save draft"}
            </Button>
          )}
        </div>
      </div>
    </>
  );
}

export function StationTemplateNewScreen() {
  return (
    <RequireAuthor>
      <StationTemplateNewScreenForm />
    </RequireAuthor>
  );
}
