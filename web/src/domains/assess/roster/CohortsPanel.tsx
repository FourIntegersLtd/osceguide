"use client";

import { useCallback, useState } from "react";
import { HiOutlineRectangleGroup } from "react-icons/hi2";
import { Alert, Button, b2bTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { PanelCard } from "@/domains/assess/team/chrome";
import { addCohort, type Cohort } from "@/domains/assess/roster/api";
import {
  DeleteCohortDialog,
  RenameCohortDialog,
} from "@/domains/assess/roster/CohortEditDialogs";

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
    <PanelCard
      title="Cohorts"
      subtitle="An intake, such as a start date. Each trainee can be in one cohort, chosen when they are added."
      icon={<HiOutlineRectangleGroup className="h-5 w-5" aria-hidden />}
    >
      {error ? (
        <Alert tone="danger" className="mb-3">
          {error}
        </Alert>
      ) : null}

      {cohorts.length === 0 ? (
        <p className="text-osce-body text-b2b-mid">
          No cohorts yet. Create one below, or leave people without.
        </p>
      ) : (
        <ul className="space-y-2" aria-label="Cohorts">
          {cohorts.map((cohort) => (
            <li
              key={cohort.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-b2b-border px-3 py-2"
            >
              <span className="min-w-0 truncate text-osce-body font-medium text-b2b-headline">
                {cohort.name}
              </span>
              <span className="flex shrink-0 items-center gap-3">
                <span className="text-osce-caption text-b2b-mid">
                  {cohort.academic_year ?? cohort.status}
                </span>
                {canManage ? (
                  <span className="flex items-center gap-2">
                    <Button
                      themeType="b2b"
                      variant="secondary"
                      size="sm"
                      onClick={() => open({ kind: "rename", cohort })}
                    >
                      Rename
                    </Button>
                    <Button
                      themeType="b2b"
                      variant="secondary"
                      size="sm"
                      onClick={() => open({ kind: "delete", cohort })}
                    >
                      Delete
                    </Button>
                  </span>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      )}

      {canManage ? (
        <div className="mt-5 border-t border-b2b-border pt-4">
          <p className="text-osce-body font-semibold text-b2b-headline">Create a cohort</p>
          <div className="mt-2 flex flex-col gap-2 sm:flex-row">
            <input
              aria-label="Cohort name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={`${b2bTokens.b2bInputBase} min-w-0 flex-1`}
              placeholder="e.g. June 2026 intake"
              autoComplete="off"
            />
            <input
              aria-label="Academic year"
              value={academicYear}
              onChange={(event) => setAcademicYear(event.target.value)}
              className={`${b2bTokens.b2bInputBase} sm:w-40`}
              placeholder="2026/27"
              autoComplete="off"
            />
            <Button
              themeType="b2b"
              variant="secondary"
              disabled={busy || name.trim() === ""}
              onClick={() => void create()}
            >
              {busy ? "Working…" : "Create cohort"}
            </Button>
          </div>
        </div>
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
    </PanelCard>
  );
}
