"use client";

import { useCallback, useMemo, useState } from "react";
import { Alert, Button, EmptyState, b2bTokens } from "@/foundation/ui";
import Table, {
  type FetchPageParams,
  type FetchPageResult,
} from "@/foundation/table/Table";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
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

  const fetchPage = useCallback(
    async (params: FetchPageParams): Promise<FetchPageResult<Trainee>> => {
      let filtered = rows;
      if (params.search) {
        const q = params.search.toLowerCase();
        filtered = rows.filter(
          (trainee) =>
            displayName(trainee).toLowerCase().includes(q) ||
            trainee.email.toLowerCase().includes(q) ||
            cohortName(cohorts, trainee.cohort_id).toLowerCase().includes(q),
        );
      }
      const start = (params.page - 1) * params.perPage;
      const end = start + params.perPage;
      return {
        items: filtered.slice(start, end),
        totalCount: filtered.length,
      };
    },
    [cohorts, rows],
  );

  const columns = useMemo(
    () => [
      {
        header: "Name",
        key: "first_name" as keyof Trainee,
        priority: "primary" as const,
        render: (trainee: Trainee) => (
          <span className={cn(b2cTableCellText, "font-medium text-osce-ink-900")}>
            {trainee.first_name || trainee.last_name ? displayName(trainee) : "None"}
          </span>
        ),
      },
      {
        header: "Email",
        key: "email" as keyof Trainee,
        render: (trainee: Trainee) => (
          <span className={cn(b2cTableCellText, "text-b2b-graphite")}>{trainee.email}</span>
        ),
      },
      {
        header: "Group",
        key: "cohort_id" as keyof Trainee,
        render: (trainee: Trainee) => (
          <span className={cn(b2cTableCellText, "text-b2b-mid")}>
            {cohortName(cohorts, trainee.cohort_id)}
          </span>
        ),
      },
      {
        header: "Access",
        key: "id" as keyof Trainee,
        render: (trainee: Trainee) =>
          accessActive(trainee) ? (
            <span className="text-osce-caption font-medium text-b2b-success-text">Active</span>
          ) : (
            <span className="text-osce-caption font-medium text-b2b-warning-text/90">Revoked</span>
          ),
      },
      {
        header: "Actions",
        key: "user_id" as keyof Trainee,
        priority: "detail" as const,
        render: (trainee: Trainee) =>
          canManage ? (
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
          ) : null,
      },
    ],
    [canManage, cohorts],
  );

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

      <Table<Trainee>
        fetchPage={fetchPage}
        columns={columns}
        idField="id"
        nameField="email"
        searchPlaceholder="Search trainees…"
        showPagination={rows.length > 10}
        defaultItemsPerPage={25}
      />

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
