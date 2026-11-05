"use client";

import { useCallback, useMemo, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  EmptyState,
  PlatformFilterBar,
  PlatformFilterSearch,
  b2bTokens,
} from "@/foundation/ui";
import Table from "@/foundation/table/Table";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import { hasCode } from "@/foundation/platform-client";
import {
  errorMessage,
  useCursorPages,
  useSearchQuery,
} from "@/foundation/hooks";
import { Dialog } from "@/domains/assess/team/chrome";
import type { Trainee } from "@/domains/assess/api";
import {
  anonymiseTrainee,
  deleteTrainee,
  listTrainees,
  readGroupMembers,
  resendInvitation,
  resendTraineeInvitations,
  revokeTrainees,
  setTraineeAccess,
  setGroupMembers,
  setTraineesCohort,
  type Cohort,
  type TraineeGroup,
} from "@/domains/assess/roster/api";
import { TraineeBulkBar } from "@/domains/assess/roster/TraineeBulkBar";
import { TraineeEditDialog } from "@/domains/assess/roster/TraineeEditDialog";
import { TraineeRowActions } from "@/domains/assess/roster/TraineeRowActions";
import {
  accessActive,
  addToGroupIds,
  addToGroupSummary,
  awaitingInvitation,
  bulkSummary,
  cohortName,
  deleteLead,
  displayName,
  rosterErrorMessage,
  traineeCountLabel,
  traineeStatus,
} from "@/domains/assess/roster/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";

type Pending = {
  kind: "revoke" | "restore" | "delete" | "anonymise";
  trainee: Trainee;
} | null;

/** The line above the table: what the last press actually did. */
type Message = { tone: "success" | "warning" | "danger"; text: string };

/**
 * Who the organisation examines.
 *
 * Revoking is the reversible removal, offered for anyone: a trainee who has
 * sat something keeps their results on revoke, where deleting the row would
 * take an examination's candidate with it. Delete exists too, since 2026-09-24,
 * offered on every row, same as the old
 * client's "Remove from team" — but the backend refuses it the moment a
 * decision is recorded (`trainee_in_use`), which is what makes it safe to
 * offer unconditionally rather than trying to know in advance.
 *
 * Correcting a row and re-sending an invitation both live here, because both
 * are things an administrator does while looking at this list. Neither is a
 * separate screen, which is where the retiring client put them: the edit modal
 * was reached from an overflow menu on a different tab from the one that showed
 * the invitation had gone unanswered.
 *
 * The list itself is one server page at a time, searched in SQL — this used to
 * take the whole roster from `Trainees` and filter and slice it in the browser,
 * which is exactly the walk that silently stopped at 2,500 rows on the
 * station catalogue. `cohorts` still comes from the parent, since every tab on
 * this screen needs the same small lookup table.
 */
export function TraineesPanel({
  orgSlug,
  cohorts,
  groups,
  canManage,
  onAddPeople,
  onChanged,
}: {
  orgSlug: string;
  cohorts: Cohort[];
  groups: TraineeGroup[];
  canManage: boolean;
  /** Opens the Add people sheet from the empty state. */
  onAddPeople: () => void;
  onChanged: () => void;
}) {
  const w = useAssessWords();
  const [pending, setPending] = useState<Pending>(null);
  const [editing, setEditing] = useState<Trainee | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Message | null>(null);
  /** Rows the backend has said have nothing pending. See `TraineeRowActions`. */
  const [settled, setSettled] = useState<Set<string>>(() => new Set());
  const [resending, setResending] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  // What the server is asked for: the box, once typing pauses.
  const query = useSearchQuery(search);

  // A page at a time, searched in SQL, rather than the whole roster walked and
  // filtered in the browser.
  const pages = useCursorPages(
    (cursor, signal) =>
      listTrainees(orgSlug, signal, { cursor, search: query }),
    [orgSlug, query],
  );
  const rows = pages.state.data ?? [];

  // Ticked rows (`trainees.id`). A new search is a new list, so it starts clear.
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [bulkBusy, setBulkBusy] = useState(false);
  const [confirmingBulkRevoke, setConfirmingBulkRevoke] = useState(false);
  const toggle = useCallback(
    (id: string) =>
      setSelected((current) => {
        const next = new Set(current);
        if (!next.delete(id)) next.add(id);
        return next;
      }),
    [],
  );

  /** Run one bulk call, say what it did, clear the selection and refresh. */
  const runBulk = useCallback(
    async (
      call: () => Promise<{ results: { outcome: string }[] } | string>,
      ok?: string,
      noun?: string,
    ) => {
      setBulkBusy(true);
      setError(null);
      setNotice(null);
      try {
        const done = await call();
        const text =
          typeof done === "string" ? done : bulkSummary(done.results, ok ?? "done", noun ?? "people");
        setNotice({ tone: "success", text });
        setSelected(new Set());
        setConfirmingBulkRevoke(false);
        pages.state.reload();
        onChanged();
      } catch (cause) {
        // A later chunk can fail after earlier ones applied, so show the true state.
        const message = errorMessage(cause);
        // The revoke dialog shows `error`; the other actions have no dialog, so say it above the table too.
        setError(message);
        setNotice({ tone: "danger", text: message });
        pages.state.reload();
        onChanged();
      } finally {
        setBulkBusy(false);
      }
    },
    [pages.state, onChanged],
  );
  const awaiting = awaitingInvitation(rows);
  // Only rows still on the loaded pages count, so a deleted row or an old search never reaches a call.
  const selectedRows = rows.filter((row) => selected.has(row.id));
  const selectedIds = selectedRows.map((row) => row.id);

  const commit = useCallback(async () => {
    if (!pending) return;
    setBusy(true);
    setError(null);
    try {
      if (pending.kind === "delete") {
        // `trainees.id`, not the user id a circuit slot names.
        await deleteTrainee(orgSlug, pending.trainee.id);
        setNotice({
          tone: "success",
          text: `Removed ${displayName(pending.trainee)} from the roster.`,
        });
      } else if (pending.kind === "anonymise") {
        await anonymiseTrainee(orgSlug, pending.trainee.id);
        setNotice({
          tone: "success",
          text: `${displayName(pending.trainee)}’s name and email address have been removed. Any results already recorded are kept.`,
        });
      } else {
        const revoking = pending.kind === "revoke";
        await setTraineeAccess(orgSlug, pending.trainee.id, revoking);
        setNotice({
          tone: "success",
          text: revoking
            ? `Revoked access for ${displayName(pending.trainee)}.`
            : `Restored access for ${displayName(pending.trainee)}.`,
        });
      }
      setPending(null);
      pages.state.reload();
      onChanged();
    } catch (cause) {
      if (pending.kind === "delete" && hasCode(cause, "trainee_in_use")) {
        setError(
          `${displayName(pending.trainee)} has a decision recorded and cannot be deleted. Revoke their access instead.`,
        );
      } else {
        setError(errorMessage(cause));
      }
    } finally {
      setBusy(false);
    }
  }, [pending, orgSlug, onChanged, pages.state]);

  /**
   * Re-send the choose-a-password link.
   *
   * `invitation_not_pending` is the one answer with a consequence the screen
   * has to keep: it means this person can already sign in, so that row stops
   * offering the button rather than offering a refusal on every press. Anything
   * else leaves the offer standing, because the next attempt may get through.
   */
  const resend = useCallback(
    async (trainee: Trainee) => {
      setResending(trainee.id);
      setError(null);
      setNotice(null);
      try {
        const invitation = await resendInvitation(orgSlug, trainee.id);
        setNotice({
          tone: "success",
          text: `Emailed ${invitation.email} a link to choose a password for ${invitation.invited_to}.`,
        });
        onChanged();
      } catch (cause) {
        if (hasCode(cause, "invitation_not_pending")) {
          setSettled((current) => new Set(current).add(trainee.id));
          setNotice({
            tone: "warning",
            text: `${displayName(trainee)}  has already set up their account, so there is no invitation to resend.`,
          });
        } else {
          setNotice({
            tone: "danger",
            text: rosterErrorMessage(cause, trainee.email),
          });
        }
      } finally {
        setResending(null);
      }
    },
    [orgSlug, onChanged],
  );

  const columns = useMemo(
    () => [
      ...(canManage
        ? [
            {
              header: "Select",
              key: "id" as keyof Trainee,
              render: (trainee: Trainee) => (
                <input
                  type="checkbox"
                  aria-label={`Select ${displayName(trainee)}`}
                  checked={selected.has(trainee.id)}
                  disabled={bulkBusy}
                  onChange={() => toggle(trainee.id)}
                />
              ),
            },
          ]
        : []),
      {
        header: "Name",
        key: "first_name" as keyof Trainee,
        priority: "primary" as const,
        render: (trainee: Trainee) => (
          <span className="flex items-center gap-3">
            <span
              aria-hidden
              className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full bg-canvas text-osce-meta text-b2b-mid"
            >
              {displayName(trainee).trim().charAt(0).toUpperCase()}
            </span>
            <span className="flex min-w-0 flex-col">
              <span
                className={cn(
                  b2cTableCellText,
                  "font-medium text-b2b-headline",
                )}
              >
                {trainee.first_name || trainee.last_name
                  ? displayName(trainee)
                  : trainee.email}
              </span>
              {trainee.first_name || trainee.last_name ? (
                <span className="truncate text-osce-meta text-b2b-mid">
                  {trainee.email}
                </span>
              ) : null}
            </span>
          </span>
        ),
      },
      {
        header: "Year group",
        key: "cohort_id" as keyof Trainee,
        render: (trainee: Trainee) => (
          <span className={cn(b2cTableCellText, "text-b2b-mid")}>
            {cohortName(cohorts, trainee.cohort_id)}
          </span>
        ),
      },
      {
        header: "Programme",
        key: "programme_names" as keyof Trainee,
        render: (trainee: Trainee) => (
          <span className={cn(b2cTableCellText, "text-b2b-mid")}>
            {trainee.programme_names?.length
              ? trainee.programme_names.join(", ")
              : "No programme"}
          </span>
        ),
      },
      {
        header: "Sat",
        key: "stations_sat" as keyof Trainee,
        render: (trainee: Trainee) => (
          <span className={cn(b2cTableCellText, "tabular-nums text-b2b-mid")}>
            {trainee.stations_sat}
          </span>
        ),
      },
      {
        header: "Status",
        key: "id" as keyof Trainee,
        render: (trainee: Trainee) => {
          const status = traineeStatus(trainee);
          return (
            <Badge variant={status.attention ? "warning" : "success"} dot>
              {status.attention ?? status.label}
            </Badge>
          );
        },
      },
      {
        header: "Actions",
        key: "user_id" as keyof Trainee,
        priority: "detail" as const,
        render: (trainee: Trainee) => (
          <TraineeRowActions
            trainee={trainee}
            invitationSettled={settled.has(trainee.id)}
            canManage={canManage}
            busy={resending === trainee.id}
            onEdit={() => {
              setError(null);
              setNotice(null);
              setEditing(trainee);
            }}
            onResend={() => void resend(trainee)}
            onAccess={() => {
              setError(null);
              setPending({
                kind: accessActive(trainee) ? "revoke" : "restore",
                trainee,
              });
            }}
            onDelete={() => {
              setError(null);
              setPending({ kind: "delete", trainee });
            }}
            onAnonymise={() => {
              setError(null);
              setPending({ kind: "anonymise", trainee });
            }}
          />
        ),
      },
    ],
    [
      canManage,
      cohorts,
      settled,
      resending,
      resend,
      selected,
      bulkBusy,
      toggle,
    ],
  );

  const revoking = pending?.kind === "revoke";
  const deleting = pending?.kind === "delete";
  const anonymising = pending?.kind === "anonymise";
  const named = pending ? displayName(pending.trainee) : "";

  return (
    <div className="min-w-0 space-y-4">
      {notice ? <Alert tone={notice.tone}>{notice.text}</Alert> : null}

      <PlatformFilterBar
        leading={
          rows.length > 0 || query ? (
            <p className={b2bTokens.b2bEyebrow}>
              {traineeCountLabel(rows.length, w)}
              {pages.hasMore ? "+" : ""}
            </p>
          ) : null
        }
      >
        <PlatformFilterSearch
          value={search}
          onChange={(value) => {
            setSearch(value);
            setSelected(new Set());
          }}
          placeholder={`Search ${w.trainees}…`}
          aria-label={`Search ${w.trainees}`}
        />
        {canManage && awaiting.length > 0 ? (
          <Button
            themeType="b2b"
            variant="secondary"
            size="sm"
            disabled={bulkBusy}
            onClick={() =>
              void runBulk(
                () =>
                  resendTraineeInvitations(
                    orgSlug,
                    awaiting.map((row) => row.id),
                  ),
                "sent",
                "invitations",
              )
            }
          >
            {`Invite everyone not signed in on this page (${awaiting.length})`}
          </Button>
        ) : null}
      </PlatformFilterBar>

      {canManage && rows.length > 0 ? (
        <TraineeBulkBar
          rowIds={rows.map((row) => row.id)}
          selected={new Set(selectedIds)}
          cohorts={cohorts}
          groups={groups}
          busy={bulkBusy}
          onSelect={setSelected}
          onResend={() =>
            void runBulk(
              // Same offer as the row control: no invitation to a revoked or signed-in person.
              () =>
                resendTraineeInvitations(
                  orgSlug,
                  awaitingInvitation(selectedRows).map((row) => row.id),
                ),
              "sent",
              "invitations",
            )
          }
          onMove={(cohortId) =>
            void runBulk(
              () => setTraineesCohort(orgSlug, selectedIds, cohortId),
              "updated",
              "people",
            )
          }
          onAddToGroup={(groupId) =>
            void runBulk(async () => {
              // PUT replaces the list, so read who is in it first and keep them, then
              // read it again: a concurrent edit can win, and the summary says so.
              const current = await readGroupMembers(orgSlug, groupId);
              await setGroupMembers(orgSlug, groupId, addToGroupIds(current, selectedIds));
              const after = await readGroupMembers(orgSlug, groupId);
              return addToGroupSummary(selectedIds, after);
            })
          }
          onRevoke={() => {
            setError(null);
            setConfirmingBulkRevoke(true);
          }}
        />
      ) : null}

      {pages.state.error ? (
        <Alert tone="danger">
          Could not load {w.trainees}.
          <button
            type="button"
            className="ml-2 underline"
            onClick={() => pages.state.reload()}
          >
            Retry
          </button>
        </Alert>
      ) : null}

      {pages.state.loading && !pages.state.data ? (
        <p className="text-osce-body text-b2c-text-secondary" role="status">
          Loading {w.trainees}…
        </p>
      ) : rows.length === 0 ? (
        query ? (
          <p className="text-osce-body text-b2b-mid">
            No {w.trainees} match &ldquo;{query}&rdquo;.
          </p>
        ) : (
          <EmptyState
            title={`No ${w.trainees} yet`}
            description={`Add ${w.trainees} so you can put them on an exam or training circuit.`}
            action={
              canManage ? (
                <Button themeType="b2b" variant="commit" onClick={onAddPeople}>
                  {w.addPeople}
                </Button>
              ) : undefined
            }
          />
        )
      ) : (
        <Table<Trainee>
          rows={rows}
          more={pages}
          themeType="b2b"
          columns={columns}
          idField="id"
        />
      )}

      {!canManage ? (
        <p className="text-osce-caption text-b2b-icon">
          <span className="font-medium">Supervisor (read only)</span>. Contact an owner or admin to
          change who has access.
        </p>
      ) : null}

      <Dialog
        open={pending != null}
        title={
          deleting
            ? `Delete ${named}?`
            : anonymising
              ? `Anonymise ${named}?`
              : revoking
                ? "Revoke access"
                : "Restore access"
        }
        lead={
          pending
            ? deleting
              ? deleteLead(named, pending.trainee.stations_sat)
              : anonymising
                ? `${named}'s name and email address will be scrubbed and their access revoked. Any decision already recorded about them is kept. This cannot be undone.`
                : revoking
                  ? `${named} will not be able to sign in or sit anything, and stays on the roster with their results intact.`
                  : `${named} will be able to sign in and sit again.`
            : ""
        }
        error={error}
        busy={busy}
        tone={deleting || anonymising || revoking ? "danger" : "commit"}
        commitLabel={
          deleting
            ? "Delete"
            : anonymising
              ? "Anonymise"
              : revoking
                ? "Revoke access"
                : "Restore access"
        }
        busyLabel={
          deleting
            ? "Deleting…"
            : anonymising
              ? "Anonymising…"
              : revoking
                ? "Revoking…"
                : "Restoring…"
        }
        onClose={() => setPending(null)}
        onCommit={() => void commit()}
      />

      <Dialog
        open={confirmingBulkRevoke}
        title={`Revoke access for ${selectedIds.length} ${selectedIds.length === 1 ? "person" : "people"}?`}
        lead="They will not be able to sign in or sit anything, and stay on the roster with their results intact."
        error={error}
        busy={bulkBusy}
        tone="danger"
        commitLabel="Revoke access"
        busyLabel="Revoking…"
        onClose={() => setConfirmingBulkRevoke(false)}
        onCommit={() =>
          void runBulk(
            () => revokeTrainees(orgSlug, selectedIds),
            "revoked",
            "people",
          )
        }
      />

      <TraineeEditDialog
        orgSlug={orgSlug}
        trainee={editing}
        cohorts={cohorts}
        onClose={() => setEditing(null)}
        onSaved={() => {
          pages.state.reload();
          onChanged();
        }}
      />
    </div>
  );
}
