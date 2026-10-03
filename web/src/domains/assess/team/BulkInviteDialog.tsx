"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { HiOutlineArrowUpTray } from "react-icons/hi2";
import { Alert, b2bTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { Dialog } from "@/domains/assess/team/chrome";
import {
  bulkInviteTeam,
  type BulkMembershipsResult,
  type Membership,
} from "@/domains/assess/team/api";
import { parseStaffCsv, teamSkipReason, type StaffCsvParse } from "@/domains/assess/team/csv";
import { roleLabel } from "@/domains/assess/team/support";

/**
 * The staff spreadsheet.
 *
 * Mirrors the trainee importer because an administrator has one habit, not two:
 * drop a .csv, see what it contained, press once. Two differences are the
 * backend's doing. There is no `password` column — an unknown address is
 * invited and chooses its own — and a person who is already on the team does not
 * fail the batch, they come back in `skipped` with the role they already hold,
 * so a sheet that half-matches the team is still worth importing.
 */
export function BulkInviteDialog({
  orgSlug,
  open,
  onClose,
  onImported,
}: {
  orgSlug: string;
  open: boolean;
  onClose: () => void;
  onImported: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [parsed, setParsed] = useState<StaffCsvParse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BulkMembershipsResult | null>(null);

  const take = useCallback(async (next: File) => {
    setFile(next);
    setResult(null);
    setError(null);
    try {
      setParsed(parseStaffCsv(await next.text()));
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

  const reset = () => {
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
      setResult(await bulkInviteTeam(orgSlug, parsed.rows));
      onImported();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [parsed, orgSlug, onImported]);

  const ready = parsed != null && parsed.error == null && parsed.rows.length > 0;
  const count = parsed?.rows.length ?? 0;

  return (
    <Dialog
      open={open}
      title="Import staff"
      lead="One spreadsheet of supervisors and admins, saved as .csv. The first row must name the columns."
      error={error}
      busy={busy}
      commitLabel={
        result ? "Done" : ready ? `Invite ${count} ${count === 1 ? "person" : "people"}` : "Import staff"
      }
      busyLabel="Importing…"
      commitDisabled={!ready && !result}
      onClose={close}
      onCommit={() => (result ? close() : void commit())}
    >
      <Instructions />

      <div
        {...getRootProps({
          className: `flex cursor-pointer flex-col items-center gap-2 rounded-panel border border-dashed p-6 text-center transition-colors ${
            isDragActive ? "border-b2b-accent bg-b2b-accent-bg" : "border-b2b-border bg-b2b-cream/60"
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
        <div className={`${b2bTokens.b2bGroupedShell} p-4 text-osce-body text-b2b-graphite`}>
          <p className="font-medium text-b2b-headline">
            {count} row{count === 1 ? "" : "s"} ready to import.
          </p>
          {parsed.skippedLines.length > 0 ? (
            <p className="mt-1 text-osce-caption text-b2b-warning-text/90">
              No email address on line{parsed.skippedLines.length === 1 ? "" : "s"}{" "}
              {parsed.skippedLines.join(", ")}, so those rows are left out.
            </p>
          ) : null}
          {parsed.badRoles.length > 0 ? (
            <p className="mt-1 text-osce-caption text-b2b-warning-text/90">
              Line{parsed.badRoles.length === 1 ? "" : "s"}{" "}
              {parsed.badRoles.map((row) => row.line).join(", ")} named a role this organisation
              cannot give. Only {roleLabel("supervisor").toLowerCase()} or{" "}
              {roleLabel("admin").toLowerCase()} can be invited, so those rows are left out.
            </p>
          ) : null}
        </div>
      ) : null}

      {result ? <Outcome result={result} /> : null}
    </Dialog>
  );
}

function Instructions() {
  return (
    <div className="space-y-3">
      <div className="rounded-panel border border-b2b-border bg-b2b-cream p-4">
        <p className="text-osce-body font-semibold text-b2b-headline">Required columns</p>
        <ul className="mt-2 space-y-1.5 text-osce-body text-b2b-graphite">
          <li>
            <span className="font-mono">email</span>. Their email address
          </li>
          <li>
            <span className="font-mono">role</span>. Either{" "}
            <span className="font-mono">supervisor</span> or{" "}
            <span className="font-mono">admin</span>
          </li>
        </ul>
      </div>
      <div className="rounded-panel border border-b2b-border bg-b2b-surface p-4">
        <p className="text-osce-body font-semibold text-b2b-headline">Example</p>
        <pre className="mt-2 overflow-auto rounded-control border border-b2b-border bg-b2b-cream p-3 text-osce-caption text-b2b-headline">
          email,role{"\n"}
          supervisor@hospital.nhs.uk,supervisor{"\n"}
          admin@hospital.nhs.uk,admin
        </pre>
      </div>
    </div>
  );
}

function Outcome({ result }: { result: BulkMembershipsResult }) {
  const created: Membership[] = result.created ?? [];
  const skipped = result.skipped ?? [];
  const invited = created.filter((member) => member.invited);

  return (
    <div className="space-y-3">
      <Alert tone={created.length > 0 ? "success" : "warning"}>
        {created.length} added, {skipped.length} skipped.
      </Alert>
      {invited.length > 0 ? (
        <p className="text-osce-caption text-b2b-mid">
          {invited.length} {invited.length === 1 ? "person was" : "people were"} emailed a link to
          choose a password. They cannot sign in until they use it.
        </p>
      ) : null}
      {skipped.length > 0 ? (
        <div className="rounded-panel border border-b2b-border bg-b2b-surface p-4">
          <p className="text-osce-body font-semibold text-b2b-headline">Not imported</p>
          <ul className="mt-2 space-y-1 text-osce-body text-b2b-graphite">
            {skipped.map((row) => (
              <li key={`${row.email}:${row.role}`}>
                <span className="font-medium text-b2b-headline">{row.email}</span>:{" "}
                {teamSkipReason(row.code)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
