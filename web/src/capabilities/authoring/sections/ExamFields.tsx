"use client";

import { useMemo, type ReactNode, type SelectHTMLAttributes } from "react";
import { Checkbox, getInputClassName, Select, b2bTokens } from "@/foundation/ui";
import { BoardSelect } from "@/foundation/ui/BoardFields";
import { boardInput } from "@/foundation/ui/boardKit";
import { LoadError } from "@/capabilities/authoring/parts/LoadError";
import { useAsync } from "@/foundation/hooks";
import { listRubrics, type Exam, type ExamSettings } from "@/capabilities/authoring/api";
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

/** The form's values for a saved exam. */
export function examToDraft(exam: Exam): ExamDraft {
  return {
    code: exam.code,
    name: exam.name,
    reading: String(exam.default_reading_seconds),
    simulation: String(exam.default_simulation_seconds),
    attempts: String(exam.station_attempt_limit),
    partnerPilot: exam.partner_pilot,
    rubricVersionId: exam.rubric_version_id ?? "",
    settings: exam.settings ?? blankExam.settings,
  };
}

/** The latest published version of each marking scheme; a selected older one stays listed. */
export function useSchemeVersions(selectedId: string) {
  const scope = useAuthoringScope();
  const rubrics = useAsync((signal) => listRubrics(scope, {}, signal), [scope.base]);
  const versions = useMemo(
    () =>
      (rubrics.data?.items ?? []).flatMap((rubric) => {
        const published = (rubric.versions ?? []).filter((v) => v.status === "published");
        const latest = Math.max(0, ...published.map((v) => v.version));
        return published
          .filter((v) => v.version === latest || v.id === selectedId)
          .map((v) => ({ id: v.id, label: `${rubric.title} · v${v.version}${rubric.owner_kind === "platform" ? " (OSCE Guide)" : ""}` }));
      }),
    [rubrics.data, selectedId],
  );
  return { rubrics, versions };
}

/** One field of the form; the board's flow it as 200px-or-wider cells. */
function FieldCell({ board, label, children }: { board: boolean; label: string; children: ReactNode }) {
  return (
    <div className={board ? "flex-[1_1_200px]" : undefined}>
      <Field board={board} label={label}>
        {children}
      </Field>
    </div>
  );
}

function SchemeSelect({ board, ...props }: { board: boolean } & SelectHTMLAttributes<HTMLSelectElement>) {
  return board ? <BoardSelect {...props} /> : <Select {...props} className="mt-1" />;
}

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
  board = false,
}: {
  value: ExamDraft;
  onChange: (next: ExamDraft) => void;
  codeDisabled?: boolean;
  /** The ExamSettings board's look: flowing 200px fields, board inputs, an open settings card. */
  board?: boolean;
}) {
  const scope = useAuthoringScope();
  const { rubrics, versions } = useSchemeVersions(value.rubricVersionId);

  const set = (patch: Partial<ExamDraft>) => onChange({ ...value, ...patch });
  const setSettings = (patch: Partial<ExamSettings>) =>
    set({ settings: { ...value.settings, ...patch } });

  const input = board ? boardInput : `mt-1 ${getInputClassName()}`;
  return (
    <>
      <div className={board ? "flex flex-wrap gap-4" : "grid grid-cols-1 gap-4 sm:grid-cols-2"}>
        {codeDisabled ? (
          <FieldCell board={board} label="Code">
            <input value={value.code} disabled className={input} />
          </FieldCell>
        ) : null}
        <FieldCell board={board} label="Name">
          <input
            value={value.name}
            onChange={(e) => set({ name: e.target.value })}
            className={input}
            placeholder="e.g. Final MB OSCE"
          />
        </FieldCell>
        <FieldCell board={board} label="Reading time (seconds)">
          <input
            type="number"
            value={value.reading}
            onChange={(e) => set({ reading: e.target.value })}
            className={input}
          />
        </FieldCell>
        <FieldCell board={board} label="Station time (seconds)">
          <input
            type="number"
            value={value.simulation}
            onChange={(e) => set({ simulation: e.target.value })}
            className={input}
          />
        </FieldCell>
        <FieldCell board={board} label="Break between stations (minutes, formal exams)">
          <input
            type="number"
            min={1}
            max={60}
            value={value.settings.default_break_minutes ?? ""}
            onChange={(e) =>
              setSettings({ default_break_minutes: e.target.value.trim() === "" ? null : Number(e.target.value) })
            }
            className={input}
          />
        </FieldCell>
        <FieldCell board={board} label="Attempts per station">
          <input
            type="number"
            value={value.attempts}
            onChange={(e) => set({ attempts: e.target.value })}
            className={input}
          />
        </FieldCell>
        <FieldCell board={board} label="Marking scheme version">
          <SchemeSelect
            board={board}
            value={value.rubricVersionId}
            onChange={(e) => set({ rubricVersionId: e.target.value })}
          >
            <option value="">{rubrics.error ? "Marking schemes could not be loaded" : "None yet"}</option>
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label}
              </option>
            ))}
          </SchemeSelect>
          {rubrics.error ? <LoadError message={rubrics.error.message} onRetry={rubrics.reload} /> : null}
        </FieldCell>
      </div>
      <ExamSettingsFields board={board} value={value.settings} onChange={setSettings} />
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
          label="Early-access partner exam"
          className="items-center"
        />
      ) : (
        <p className={board ? b2bTokens.assessMeta : "text-osce-caption text-ink-muted"}>
          Partner-pilot status is set by OSCE Guide staff, not from here.
        </p>
      )}
    </>
  );
}
