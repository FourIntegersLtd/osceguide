"use client";

import { useState } from "react";
import { Alert, Button, EmptyState, b2bTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { Dialog } from "@/domains/assess/team/chrome";
import type { Trainee } from "@/domains/assess/api";
import { setTraineeAccess, type Cohort } from "@/domains/assess/roster/api";
import {
  accessActive,
  cohortName,
  displayName,
  sortTrainees,
  traineeCountLabel,
} from "@/domains/assess/roster/support";

const TABLE_CLASS = "min-w-full w-full divide-y divide-b2b-border";
const CELL = "px-4 py-3 text-osce-body align-middle";

/**
 * Who the organisation examines.
 *
 * Revoking is the only removal the platform offers: a trainee has sat things,
 * and deleting the row would take an examination's candidate with it. The old
 * client had a "Remove from team" that deleted the record outright — see
 * `docs/port-gaps.md`.
 */
export function TraineesPanel({
  orgSlug,
  trainees,
  cohorts,
  canManage,
  onChanged,
}: {
  orgSlug: string;
  trainees: Trainee[];
  cohorts: Cohort[];
  canManage: boolean;
  onChanged: () => void;
}) {
  const rows = sortTrainees(trainees);
  const [pending, setPending] = useState<Trainee | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function commit() {
    if (!pending) return;
    setBusy(true);
    setError(null);
    const revoking = accessActive(pending);
    try {
      // `trainees.id`, not the user id a circuit slot names.
      await setTraineeAccess(orgSlug, pending.id, revoking);
      setNotice(
        revoking
          ? `Revoked access for ${displayName(pending)}.`
          : `Restored access for ${displayName(pending)}.`,
      );
      setPending(null);
      onChanged();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  if (rows.length === 0) {
    return (
      <EmptyState
        title="No trainees yet"
        description="Add trainees so you can put them on an exam or training circuit."
      />
    );
  }

  const revoking = pending ? accessActive(pending) : false;

  return (
    <div className="min-w-0 space-y-4">
      {notice ? <Alert tone="success">{notice}</Alert> : null}
      <p className={b2bTokens.b2bEyebrow}>{traineeCountLabel(rows.length)}</p>

      <div className={b2bTokens.b2bGroupedShell}>
        <div className={b2bTokens.b2bTableScroll}>
          <table className={TABLE_CLASS}>
            <thead>
              <tr>
                {["Name", "Email", "Group", "Access", ""].map((header, index) => (
                  <th
                    key={header || index}
                    scope="col"
                    className="px-4 py-2 text-left text-osce-caption font-medium text-b2b-mid"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-b2b-border">
              {rows.map((trainee) => (
                <tr key={trainee.id}>
                  <td className={`${CELL} min-w-[8rem]`}>
                    <span className="font-medium text-b2b-headline">
                      {trainee.first_name || trainee.last_name
                        ? displayName(trainee)
                        : "None"}
                    </span>
                  </td>
                  <td className={`${CELL} min-w-[11rem] text-b2b-graphite`}>{trainee.email}</td>
                  <td className={`${CELL} min-w-[6rem] text-b2b-mid`}>
                    {cohortName(cohorts, trainee.cohort_id)}
                  </td>
                  <td className={`${CELL} min-w-[5rem]`}>
                    {accessActive(trainee) ? (
                      <span className="text-osce-caption font-medium text-b2b-success-text">
                        Active
                      </span>
                    ) : (
                      <span className="text-osce-caption font-medium text-b2b-warning-text/90">
                        Revoked
                      </span>
                    )}
                  </td>
                  <td className={`${CELL} text-right`}>
                    {canManage ? (
                      <Button
                        themeType="b2b"
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          setError(null);
                          setPending(trainee);
                        }}
                      >
                        {accessActive(trainee) ? "Revoke" : "Restore"}
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {!canManage ? (
        <p className="text-osce-caption text-b2b-icon">
          Contact an owner or admin to change who has access.
        </p>
      ) : null}

      <Dialog
        open={pending != null}
        title={revoking ? "Revoke access" : "Restore access"}
        lead={
          pending
            ? revoking
              ? `${displayName(pending)} will not be able to sign in or sit anything, and stays on the roster with their results intact.`
              : `${displayName(pending)} will be able to sign in and sit again.`
            : ""
        }
        error={error}
        busy={busy}
        tone={revoking ? "danger" : "commit"}
        commitLabel={revoking ? "Revoke access" : "Restore access"}
        busyLabel={revoking ? "Revoking…" : "Restoring…"}
        onClose={() => setPending(null)}
        onCommit={() => void commit()}
      />
    </div>
  );
}
