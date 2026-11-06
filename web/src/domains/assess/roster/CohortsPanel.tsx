"use client";

import { useCallback, useState } from "react";
import { b2bTokens as t, cn } from "@/foundation/ui";
import { Fold, Note, card, h2, row } from "@/domains/assess/ui";
import { errorMessage } from "@/foundation/hooks";
import { addCohort, type Cohort } from "@/domains/assess/roster/api";
import {
  DeleteCohortDialog,
  RenameCohortDialog,
} from "@/domains/assess/roster/CohortEditDialogs";
import { boardBtn, boardPadWide, boardInput, boardButtonSmall } from "@/foundation/ui/boardKit";

type Pending =
  | { kind: "rename"; cohort: Cohort }
  | { kind: "delete"; cohort: Cohort }
  | null;

/**
 * Intakes.
 *
 * A cohort is a row with an id and every trainee points at it, so a rename is
 * one PATCH and nobody's record drifts — the thing the retiring client got
 * wrong by copying a label onto two hundred people. Deleting is refused outright
 * while anybody still belongs to it, because a silent clear would leave those
 * people looking as though they had never had an intake; the refusal says so and
 * the fix is one trainee edit at a time on the Trainees tab.
 *
 * Both dialogs live in `CohortEditDialogs` because each carries its own busy and
 * error state; this file is the list, the create form and the one error area
 * they share.
 */
export function CohortsPanel({
  orgSlug,
  cohorts,
  canManage,
  onChanged,
}: {
  orgSlug: string;
  cohorts: Cohort[];
  canManage: boolean;
  onChanged: () => void;
}) {
  const [name, setName] = useState("");
  const [academicYear, setAcademicYear] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<Pending>(null);

  const create = useCallback(async () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setBusy(true);
    setError(null);
    try {
      await addCohort(orgSlug, { name: trimmed, academicYear: academicYear.trim() || null });
      setName("");
      setAcademicYear("");
      onChanged();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [orgSlug, name, academicYear, onChanged]);

  const open = (next: NonNullable<Pending>) => {
    setError(null);
    setPending(next);
  };

  return (
    <div className={boardPadWide}>
      <h2 className={h2}>Year groups</h2>
      <p className={cn(t.assessMeta, "m-0")}>
        An intake, such as a start date. Each trainee can be in one year group, chosen when they are added.
      </p>
      {error ? <Note tone="bad">{error}</Note> : null}

      {cohorts.length === 0 ? (
        <p className={cn(t.assessMeta, "m-0")}>No year groups yet. Create one below, or leave people without.</p>
      ) : (
        <ul className={card} aria-label="Year groups">
          {cohorts.map((cohort, index) => (
            <li key={cohort.id} className={cn(row, "gap-2", index === 0 && "border-t-0")}>
              <span className="flex-1">
                {cohort.name}
                <div className={t.assessMeta}>{cohort.academic_year ?? cohort.status}</div>
              </span>
              {canManage ? (
                <>
                  <button type="button" className={boardButtonSmall} onClick={() => open({ kind: "rename", cohort })}>
                    Rename
                  </button>
                  <button type="button" className={boardButtonSmall} onClick={() => open({ kind: "delete", cohort })}>
                    Delete
                  </button>
                </>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {canManage ? (
        <Fold title="Create a year group">
          <input
            aria-label="Year group name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            className={boardInput}
            placeholder="e.g. June 2026 intake"
            autoComplete="off"
          />
          <input
            aria-label="Academic year"
            value={academicYear}
            onChange={(event) => setAcademicYear(event.target.value)}
            className={boardInput}
            placeholder="2026/27"
            autoComplete="off"
          />
          <button type="button" className={cn(boardBtn("primary", true), "self-start")} disabled={busy || name.trim() === ""} onClick={() => create()}>
            {busy ? "Working…" : "Create year group"}
          </button>
        </Fold>
      ) : null}

      <RenameCohortDialog
        orgSlug={orgSlug}
        cohort={pending?.kind === "rename" ? pending.cohort : null}
        onClose={() => setPending(null)}
        onSaved={onChanged}
      />

      <DeleteCohortDialog
        orgSlug={orgSlug}
        cohort={pending?.kind === "delete" ? pending.cohort : null}
        onClose={() => setPending(null)}
        onDeleted={onChanged}
      />
    </div>
  );
}
