"use client";

import { useMemo, useState } from "react";
import { b2bTokens as t, cn } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { PeopleDialog as Dialog, Note, hint } from "@/domains/assess/ui";
import { boardInput, boardLabel } from "@/foundation/ui/boardKit";
import { addCohort, bulkAddTrainees, type BulkTraineesResult, type Cohort } from "@/domains/assess/roster/api";
import { skipReason } from "@/domains/assess/roster/csv";
import { importSummary } from "@/domains/assess/roster/csv";
import {
  addCandidatesBlocked,
  addCandidatesLabel,
  duplicateWarning,
  parsePastedEmails,
} from "@/domains/assess/people/candidatesView";

/**
 * Add candidates (HireCandidates.dc.html): emails one per line and an intake, in one dialog. The
 * spreadsheet and the one-person form (name, temporary password) stay a link away, as the sheets
 * they always were. An intake typed here that does not exist yet is created, as a spreadsheet's is.
 */
export function AddCandidatesDialog({
  orgSlug,
  open,
  cohorts,
  existingEmails,
  onClose,
  onAdded,
  onSpreadsheet,
  onOne,
}: {
  orgSlug: string;
  open: boolean;
  cohorts: Cohort[];
  existingEmails: string[];
  onClose: () => void;
  onAdded: () => void;
  onSpreadsheet: () => void;
  onOne: () => void;
}) {
  const [text, setText] = useState("");
  const [intake, setIntake] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BulkTraineesResult | null>(null);
  const parsed = useMemo(() => parsePastedEmails(text, existingEmails), [text, existingEmails]);
  const warning = duplicateWarning(parsed.duplicates);
  const blocked = addCandidatesBlocked(parsed, busy);

  const close = () => {
    if (busy) return;
    setText("");
    setIntake("");
    setResult(null);
    setError(null);
    onClose();
  };

  const commit = async () => {
    setBusy(true);
    setError(null);
    try {
      const name = intake.trim();
      let cohortId: string | null = null;
      if (name) {
        const known = cohorts.find((c) => c.name.trim().toLowerCase() === name.toLowerCase());
        cohortId = known ? known.id : (await addCohort(orgSlug, { name, academicYear: null })).id;
      }
      const outcome = await bulkAddTrainees(
        orgSlug,
        parsed.emails.map((email) => ({ email, firstName: null, lastName: null, cohortId })),
      );
      setResult(outcome);
      onAdded();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  const skipped = result?.skipped ?? [];
  return (
    <Dialog
      open={open}
      title="Add candidates"
      error={error}
      busy={busy}
      commitLabel={result ? "Done" : addCandidatesLabel(parsed.emails.length)}
      busyLabel="Adding…"
      commitDisabled={!result && blocked !== null}
      onClose={close}
      onCommit={() => (result ? close() : void commit())}
    >
      {result ? (
        <>
          <Note tone={(result.created ?? []).length > 0 ? "ok" : "warn"}>
            {importSummary((result.created ?? []).length, skipped.length, parsed.invalid.length)}
          </Note>
          {skipped.length > 0 ? (
            <ul className="m-0 list-none p-0 text-assess-label">
              {skipped.map((row) => (
                <li key={row.email}>{row.email}: {skipReason(row.code).replace("already on the roster", "already a candidate")}</li>
              ))}
            </ul>
          ) : null}
        </>
      ) : (
        <>
          <div>
            <label htmlFor="add-candidates-emails" className={boardLabel}>Emails, one per line</label>
            <textarea
              id="add-candidates-emails"
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows={5}
              className={boardInput}
              placeholder="priya.shah@mail.com"
              autoComplete="off"
            />
            <div className={hint}>
              Or{" "}
              <button type="button" className="text-osce-accent hover:text-osce-accent-hover" onClick={onSpreadsheet}>
                upload a spreadsheet
              </button>{" "}
              with name and email columns. To add one with a name or a temporary password,{" "}
              <button type="button" className="text-osce-accent hover:text-osce-accent-hover" onClick={onOne}>
                add one candidate
              </button>
              .
            </div>
          </div>
          <div>
            <label htmlFor="add-candidates-intake" className={boardLabel}>Intake</label>
            <input
              id="add-candidates-intake"
              value={intake}
              onChange={(event) => setIntake(event.target.value)}
              list="add-candidates-intakes"
              className={boardInput}
              placeholder="e.g. November intake"
              autoComplete="off"
            />
            <datalist id="add-candidates-intakes">
              {cohorts.map((c) => (
                <option key={c.id} value={c.name} />
              ))}
            </datalist>
          </div>
          {warning ? <Note tone="warn">{warning}</Note> : null}
          {blocked ? <p className={cn(t.assessMeta, "m-0")}>{blocked}</p> : null}
        </>
      )}
    </Dialog>
  );
}
