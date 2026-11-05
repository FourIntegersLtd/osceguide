"use client";

import { useCallback, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";
import { HiOutlineArrowUpTray } from "react-icons/hi2";
import { Alert, Checkbox, b2bTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { Dialog } from "@/domains/assess/team/chrome";
import {
  addCohort,
  bulkAddTrainees,
  type BulkTraineesResult,
  type Cohort,
} from "@/domains/assess/roster/api";
import {
  parseTraineeCsv,
  skipReason,
  type CsvParse,
} from "@/domains/assess/roster/csv";
import {
  ImportInstructions,
  ImportOutcome,
} from "@/domains/assess/roster/ImportParts";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * The spreadsheet import.
 *
 * Two things changed from the old modal and both are the backend's doing.
 * There is no `password` column any more — an unknown address is invited and
 * chooses its own — and a `cohort` column names a cohort that must already
 * exist, because the platform has cohort rows with ids rather than a free-text
 * label copied onto every trainee. Unrecognised names are reported before
 * anything is sent rather than quietly imported as nothing.
 */
export function BulkImportDialog({
  orgSlug,
  open,
  cohorts,
  onClose,
  onImported,
}: {
  orgSlug: string;
  open: boolean;
  cohorts: Cohort[];
  onClose: () => void;
  onImported: () => void;
}) {
  const w = useAssessWords();
  const [file, setFile] = useState<File | null>(null);
  const [parsed, setParsed] = useState<CsvParse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BulkTraineesResult | null>(null);

  const take = useCallback(async (next: File) => {
    setFile(next);
    setResult(null);
    setError(null);
    try {
      setParsed(parseTraineeCsv(await next.text()));
    } catch (cause) {
      setParsed(null);
      setError(errorMessage(cause));
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { "text/csv": [".csv"] },
    multiple: false,
    onDrop: (files) => {
      if (files[0]) void take(files[0]);
    },
  });

  // Ticked: the cohorts the file names are created as part of the import, not before it.
  const [createMissing, setCreateMissing] = useState(false);
  const byName = useMemo(
    () =>
      new Map(
        cohorts.map((cohort) => [cohort.name.trim().toLowerCase(), cohort.id]),
      ),
    [cohorts],
  );
  const unknownCohorts = useMemo(
    () =>
      parsed
        ? [
            ...new Set(
              parsed.rows
                .map((row) => row.cohort)
                .filter((label): label is string => Boolean(label))
                .filter((label) => !byName.has(label.trim().toLowerCase())),
            ),
          ]
        : [],
    [parsed, byName],
  );

  const reset = () => {
    setCreateMissing(false);
    setFile(null);
    setParsed(null);
    setResult(null);
    setError(null);
  };

  const close = () => {
    if (busy) return;
    reset();
    onClose();
  };

  const commit = useCallback(async () => {
    if (!parsed || parsed.rows.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const ids = new Map(byName);
      if (createMissing) {
        for (const name of unknownCohorts) {
          ids.set(
            name.trim().toLowerCase(),
            (await addCohort(orgSlug, { name, academicYear: null })).id,
          );
        }
      }
      const outcome = await bulkAddTrainees(
        orgSlug,
        parsed.rows.map((row) => ({
          email: row.email,
          firstName: row.firstName,
          lastName: row.lastName,
          cohortId: row.cohort
            ? (ids.get(row.cohort.trim().toLowerCase()) ?? null)
            : null,
        })),
      );
      setResult(outcome);
      onImported();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [parsed, orgSlug, byName, createMissing, unknownCohorts, onImported]);

  const ready =
    parsed != null && parsed.error == null && parsed.rows.length > 0;

  return (
    <Dialog
      open={open}
      title={`Import ${w.trainees}`}
      lead={`One spreadsheet of ${w.trainees}, saved as .csv. The first row must name the columns.`}
      error={error}
      busy={busy}
      commitLabel={
        result
          ? "Done"
          : ready
            ? `Import ${parsed.rows.length} ${parsed.rows.length === 1 ? w.trainee : w.trainees}`
            : `Import ${w.trainees}`
      }
      busyLabel="Importing…"
      commitDisabled={!ready && !result}
      onClose={close}
      onCommit={() => (result ? close() : void commit())}
    >
      <ImportInstructions />

      <div
        {...getRootProps({
          className: `flex cursor-pointer flex-col items-center gap-2 rounded-panel border border-dashed p-6 text-center transition-colors ${
            isDragActive
              ? "border-b2b-accent bg-b2b-accent-bg"
              : "border-b2b-border bg-b2b-cream/60"
          }`,
        })}
      >
        <input {...getInputProps()} />
        <HiOutlineArrowUpTray className="h-6 w-6 text-b2b-accent" aria-hidden />
        <p className="text-osce-body font-medium text-b2b-headline">
          {file ? file.name : "Drop your .csv here, or choose a file"}
        </p>
        <p className="text-osce-caption text-b2b-mid">
          {file ? `${(file.size / 1024).toFixed(1)} KB` : ".csv files only"}
        </p>
      </div>

      {parsed?.error ? <Alert tone="danger">{parsed.error}</Alert> : null}

      {ready && !result ? (
        <div
          className={`${b2bTokens.b2bGroupedShell} p-4 text-osce-body text-b2b-graphite`}
        >
          <p className="font-medium text-b2b-headline">
            {parsed.rows.length} row{parsed.rows.length === 1 ? "" : "s"} ready
            to import.
          </p>
          {parsed.skippedLines.length > 0 ? (
            <p className="mt-1 text-osce-caption text-b2b-warning-text/90">
              No email address on line
              {parsed.skippedLines.length === 1 ? "" : "s"}{" "}
              {parsed.skippedLines.join(", ")}, so those rows are left out.
            </p>
          ) : null}
          {parsed.invalidLines.length > 0 ? (
            <p className="mt-1 text-osce-caption text-b2b-warning-text/90">
              Line{parsed.invalidLines.length === 1 ? "" : "s"}{" "}
              {parsed.invalidLines.join(", ")}: not a valid email address, so{" "}
              {parsed.invalidLines.length === 1
                ? "that row is"
                : "those rows are"}{" "}
              left out.
            </p>
          ) : null}
          {parsed.duplicateLines.length > 0 ? (
            <p className="mt-1 text-osce-caption text-b2b-warning-text/90">
              Line{parsed.duplicateLines.length === 1 ? "" : "s"}{" "}
              {parsed.duplicateLines.join(", ")}: the address already appears
              earlier in the file, so{" "}
              {parsed.duplicateLines.length === 1 ? "it is" : "they are"}{" "}
              counted once.
            </p>
          ) : null}
          {unknownCohorts.length > 0 ? (
            <div className="mt-1 text-osce-caption text-b2b-warning-text/90">
              <p>No year group here is called {unknownCohorts.join(", ")}.</p>
              <Checkbox
                label={`Create ${unknownCohorts.length === 1 ? "that year group" : "those year groups"} when importing`}
                checked={createMissing}
                onChange={() => setCreateMissing((on) => !on)}
              />
              {createMissing ? null : (
                <p>Otherwise those people are added with no year group.</p>
              )}
            </div>
          ) : null}
        </div>
      ) : null}

      {result ? <ImportOutcome result={result} describe={skipReason} /> : null}
    </Dialog>
  );
}
