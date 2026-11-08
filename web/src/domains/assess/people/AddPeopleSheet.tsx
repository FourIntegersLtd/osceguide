"use client";

import { boardTab, boardTabs, boardBtn, boardPadWide } from "@/foundation/ui/boardKit";
import { useState } from "react";
import { b2bTokens as t, cn } from "@/foundation/ui";
import { BulkImportDialog } from "@/domains/assess/roster/BulkImportDialog";
import { AddTraineePanel } from "@/domains/assess/roster/AddTraineePanel";
import { BulkInviteDialog } from "@/domains/assess/team/BulkInviteDialog";
import { InvitePanel } from "@/domains/assess/team/InvitePanel";
import type { Cohort } from "@/domains/assess/roster/api";
import { useAssessWords } from "@/capabilities/assess-words";
import { h2 } from "@/domains/assess/ui";

export type AddKind = "trainees" | "staff";

type Mode = "trainee" | "trainee-sheet" | "staff" | "staff-sheet";

/**
 * The one "Add people" page (AddPeople.dc.html): a back link, a title and four states: one trainee,
 * a trainee spreadsheet, a staff invitation, a staff spreadsheet. It wraps the two existing panels, so
 * their rules (duplicates reported, never fatal) stay where they were. The spreadsheet states are the
 * existing import dialogs, opened over a card that names them.
 */
export function AddPeopleSheet({
  orgSlug,
  initialKind,
  cohorts,
  canManage,
  onTraineesAdded,
  onStaffAdded,
  onClose,
}: {
  orgSlug: string;
  initialKind: AddKind;
  cohorts: Cohort[];
  canManage: boolean;
  onTraineesAdded: () => void;
  onStaffAdded: () => void;
  onClose: () => void;
}) {
  const w = useAssessWords();
  const [mode, setMode] = useState<Mode>(
    initialKind === "staff" ? "staff" : "trainee",
  );
  const modes: { key: Mode; label: string }[] = [
    { key: "trainee", label: `${w.Trainee}: one person` },
    { key: "trainee-sheet", label: `${w.Trainees}: spreadsheet` },
    { key: "staff", label: w.hiring ? `${w.Supervisors}: invite` : "Staff: invite" },
    { key: "staff-sheet", label: w.hiring ? `${w.Supervisors}: spreadsheet` : "Staff: spreadsheet" },
  ];
  const sheet = mode === "trainee-sheet" || mode === "staff-sheet";
  const back = mode === "trainee-sheet" ? "trainee" : "staff";

  return (
    <div
      data-testid="addpeople-page"
      className="flex min-w-0 flex-col gap-6"
    >
      <div>
        <button
          type="button"
          className="text-assess-label text-osce-accent hover:text-osce-accent-hover"
          onClick={onClose}
        >
          ‹ {w.People}
        </button>
      </div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className={t.assessEyebrow}>Organise</div>
          <h1 className={t.assessTitle}>{w.addPeople}</h1>
          <p className={t.assessDesc}>
            {w.hiring
              ? `Add the ${w.trainees} you are assessing, or invite ${w.supervisors} to run and mark.`
              : `Add the ${w.trainees} who will sit your exams or training sessions, or invite staff to run and mark them.`}
          </p>
        </div>
        {/* The board's (empty) actions slot: it wraps under the text on a narrow screen, as drawn. */}
        <div aria-hidden className="flex flex-wrap items-center gap-2.5" />
      </div>
      <div
        className={boardTabs}
        role="tablist"
        aria-label="Who to add"
      >
        {modes.map((entry) => (
          <button
            key={entry.key}
            type="button"
            role="tab"
            aria-selected={mode === entry.key}
            onClick={() => setMode(entry.key)}
            className={boardTab(mode === entry.key)}
          >
            {entry.label}
          </button>
        ))}
      </div>
      {mode === "trainee" ? (
        <AddTraineePanel
          orgSlug={orgSlug}
          cohorts={cohorts}
          canManage={canManage}
          onAdded={onTraineesAdded}
        />
      ) : null}
      {mode === "staff" ? (
        <InvitePanel
          orgSlug={orgSlug}
          canManage={canManage}
          onInvited={onStaffAdded}
        />
      ) : null}
      {sheet ? (
        <div className={boardPadWide}>
          <h2 className={h2}>
            {mode === "trainee-sheet" ? `Add ${w.trainees} from a spreadsheet` : w.hiring ? `Add ${w.supervisors} from a spreadsheet` : "Add staff from a spreadsheet"}
          </h2>
          <p className={cn(t.assessMeta, "m-0")}>
            {mode === "trainee-sheet"
              ? `One spreadsheet of ${w.trainees}, saved as .csv. The first row must name the columns.`
              : `One spreadsheet of ${w.supervisors} and admins, saved as .csv. The first row must name the columns.`}
          </p>
          <button
            type="button"
            className={cn(boardBtn(), "self-start")}
            onClick={() => setMode(back)}
          >
            Back to adding one person
          </button>
        </div>
      ) : null}
      {mode === "trainee-sheet" ? (
        <BulkImportDialog
          orgSlug={orgSlug}
          open
          cohorts={cohorts}
          onClose={() => setMode("trainee")}
          onImported={onTraineesAdded}
        />
      ) : null}
      {mode === "staff-sheet" ? (
        <BulkInviteDialog
          orgSlug={orgSlug}
          open
          onClose={() => setMode("staff")}
          onImported={onStaffAdded}
        />
      ) : null}
    </div>
  );
}
