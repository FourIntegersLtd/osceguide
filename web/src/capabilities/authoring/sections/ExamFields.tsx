"use client";

import { useMemo } from "react";
import { Checkbox, getInputClassName, Select } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { listRubrics, type ExamSettings } from "@/capabilities/authoring/api";
import {
  ExamSettingsFields,
  Field,
} from "@/capabilities/authoring/sections/ExamSettingsFields";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";

export interface ExamDraft {
  code: string;
  name: string;
  reading: string;
  simulation: string;
  attempts: string;
  partnerPilot: boolean;
  rubricVersionId: string;
  /**
   * The whole settings object, sent back whole: the backend replaces it on
   * save, so subtypes and prompt keys this form does not show survive by
   * riding along untouched.
   */
  settings: ExamSettings;
}

/** The backend's `ExamSettings` defaults, which `{}` would mean anyway. */
const defaultSettings: ExamSettings = {
  date_label: "Exam date",
  session_modes: ["debrief", "practice_as_patient"],
  help_modes: ["navigate"],
  show_tips_while_marking: false,
  peer_waiting_email: false,
  station_subtypes: [],
};

/** The backend's own defaults, so a blank form creates a working exam. */
export const blankExam: ExamDraft = {
  code: "",
  name: "",
  reading: "120",
  simulation: "600",
  attempts: "3",
  partnerPilot: false,
  rubricVersionId: "",
  settings: defaultSettings,
};

/**
 * The exam form, shared by create and edit.
 *
 * Create and edit took the same seven fields in the old client and were two
 * components, which is how they came to disagree about the attempt limit's
 * default.
 */
export function ExamFields({
  value,
  onChange,
  codeDisabled = false,
}: {
  value: ExamDraft;
  onChange: (next: ExamDraft) => void;
  codeDisabled?: boolean;
}) {
  const scope = useAuthoringScope();
  const rubrics = useAsync(
    (signal) => listRubrics(scope, {}, signal),
    [scope.base],
  );

  // The latest published version of each rubric; a selected older one stays listed.
  const versions = useMemo(
    () =>
      (rubrics.data?.items ?? []).flatMap((rubric) => {
        const published = (rubric.versions ?? []).filter((v) => v.status === "published");
        const latest = Math.max(0, ...published.map((v) => v.version));
        return published
          .filter((v) => v.version === latest || v.id === value.rubricVersionId)
          .map((v) => ({ id: v.id, label: `${rubric.title} · v${v.version}` }));
      }),
    [rubrics.data, value.rubricVersionId],
  );

  const set = (patch: Partial<ExamDraft>) => onChange({ ...value, ...patch });
  const setSettings = (patch: Partial<ExamSettings>) =>
    set({ settings: { ...value.settings, ...patch } });

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Code">
          <input
            value={value.code}
            disabled={codeDisabled}
            onChange={(e) => set({ code: e.target.value })}
            className={`mt-1 ${getInputClassName()}`}
            placeholder="e.g. finals"
          />
        </Field>
        <Field label="Name">
          <input
            value={value.name}
            onChange={(e) => set({ name: e.target.value })}
            className={`mt-1 ${getInputClassName()}`}
            placeholder="e.g. Final MB OSCE"
          />
        </Field>
        <Field label="Reading time (seconds)">
          <input
            type="number"
            value={value.reading}
            onChange={(e) => set({ reading: e.target.value })}
            className={`mt-1 ${getInputClassName()}`}
          />
        </Field>
        <Field label="Station time (seconds)">
          <input
            type="number"
            value={value.simulation}
            onChange={(e) => set({ simulation: e.target.value })}
            className={`mt-1 ${getInputClassName()}`}
          />
        </Field>
        <Field label="Attempts per station">
          <input
            type="number"
            value={value.attempts}
            onChange={(e) => set({ attempts: e.target.value })}
            className={`mt-1 ${getInputClassName()}`}
          />
        </Field>
        <Field label="Marking scheme version">
          <Select
            value={value.rubricVersionId}
            onChange={(e) => set({ rubricVersionId: e.target.value })}
            className="mt-1"
          >
            <option value="">{rubrics.error ? "Marking schemes could not be loaded" : "None yet"}</option>
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label}
              </option>
            ))}
          </Select>
          {rubrics.error ? (
            <p role="alert" className="mt-1 text-osce-caption text-danger">
              {rubrics.error.message}{" "}
              <button type="button" onClick={rubrics.reload} className="underline">
                Try again
              </button>
            </p>
          ) : null}
        </Field>
      </div>
      <ExamSettingsFields value={value.settings} onChange={setSettings} />
      {/*
       * The backend refuses this on the org-scoped route on purpose — "a
       * school cannot put its own private exam into the funnel by asking"
       * (`test_an_org_exam_is_never_a_partner_pilot`) — and silently writes
       * `false` regardless of what this box says. Offering it here would be a
       * control that lies about what pressing it does, so it is shown only
       * where the write actually takes.
       */}
      {scope.kind === "platform" ? (
        <Checkbox
          checked={value.partnerPilot}
          onChange={(e) => set({ partnerPilot: e.target.checked })}
          label="Partner pilot"
          className="items-center"
        />
      ) : (
        <p className="text-osce-caption text-ink-muted">
          Partner-pilot status is set by OSCE Guide staff, not from here.
        </p>
      )}
    </>
  );
}
