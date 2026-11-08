"use client";

import { useCallback, useState } from "react";
import { b2bTokens as t, cn } from "@/foundation/ui";
import { Chip, Note, card, h2, row, th, PeopleDialog as Dialog } from "@/domains/assess/ui";
import { hasCode } from "@/foundation/platform-client";
import {
  errorMessage,
  useCursorPages,
  useSearchQuery,
} from "@/foundation/hooks";
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
import { EraseDataDialog } from "@/domains/assess/roster/EraseDataDialog";
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
import { useAssessWords } from "@/capabilities/assess-words";
import { say } from "@/domains/assess/roster/rosterWords";
import {
  CANDIDATES_BULK_HINT,
  CANDIDATES_EMPTY,
  CANDIDATES_SEARCH,
  candidatePills,
  candidateStatus,
  filterByPill,
  type CandidatePillKey,
} from "@/domains/assess/people/candidatesView";
import { boardBtn, boardPadWide, boardInput, boardAvatar, boardButtonSmall } from "@/foundation/ui/boardKit";

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
  total,
  onAddPeople,
  onChanged,
}: {
  orgSlug: string;
  cohorts: Cohort[];
  groups: TraineeGroup[];
  canManage: boolean;
  /** How many people the roster holds in all, for the All pill on a hire workspace. */
  total?: number;
  /** Opens the Add people sheet from the empty state. */
  onAddPeople: () => void;
  onChanged: () => void;
}) {
  const w = useAssessWords();
  const [pending, setPending] = useState<Pending>(null);
  const [erasing, setErasing] = useState<Trainee | null>(null);
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
  const allRows = pages.state.data ?? [];
  const [pill, setPill] = useState<CandidatePillKey>("all");
  // Pills are a hire layout; an institution never leaves "all".
  const rows = w.hiring ? filterByPill(allRows, pill) : allRows;

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
          typeof done === "string" ? done : bulkSummary(done.results, ok ?? "done", say(w, noun ?? "people"));
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
    [pages.state, onChanged, w],
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
          text: say(w, `Removed ${displayName(pending.trainee)} from the roster.`),
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
  }, [pending, orgSlug, onChanged, pages.state, w]);

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
            text: rosterErrorMessage(cause, trainee.email, w),
          });
        }
      } finally {
        setResending(null);
      }
    },
    [orgSlug, onChanged, w],
  );

  const revoking = pending?.kind === "revoke";
  const deleting = pending?.kind === "delete";
  const anonymising = pending?.kind === "anonymise";
  const named = pending ? displayName(pending.trainee) : "";

  return (
    <div className="flex min-w-0 flex-col gap-6">
      {notice ? <Note tone={notice.tone === "success" ? "ok" : notice.tone === "warning" ? "warn" : "bad"}>{notice.text}</Note> : null}

      <div className="flex flex-wrap items-center gap-3">
        {!w.hiring && (rows.length > 0 || query) ? (
          <span className={t.assessEyebrow}>
            {traineeCountLabel(rows.length, w)}
            {pages.hasMore ? "+" : ""}
          </span>
        ) : null}
        <input
          className={cn(boardInput, "flex-[1_1_260px] !w-auto")}
          type="search"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setSelected(new Set());
          }}
          placeholder={w.hiring ? CANDIDATES_SEARCH : `Search ${w.trainees}…`}
          aria-label={`Search ${w.trainees}`}
        />
        {canManage && awaiting.length > 0 ? (
          <button
            type="button"
            className={boardBtn()}
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
          </button>
        ) : null}
      </div>

      {w.hiring && (allRows.length > 0 || query) ? (
        <div className="flex flex-wrap items-center gap-2" role="group" aria-label={`Filter ${w.trainees}`}>
          {candidatePills(allRows, cohorts, total ?? allRows.length, pages.hasMore).map((entry) => {
            const key = typeof entry.key === "string" ? entry.key : entry.key.intake;
            const on = typeof entry.key === "string" ? pill === entry.key : typeof pill !== "string" && pill.intake === entry.key.intake;
            return (
              <button key={key} type="button" aria-pressed={on} onClick={() => { setPill(entry.key); setSelected(new Set()); }} className={cn("rounded-full border px-3 py-1 text-assess-label", on ? "border-osce-accent bg-osce-accent text-white" : "border-osce-border bg-osce-surface text-osce-ink-900")}>
                {entry.label}
              </button>
            );
          })}
        </div>
      ) : null}

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
              return addToGroupSummary(selectedIds, after, w);
            })
          }
          onRevoke={() => {
            setError(null);
            setConfirmingBulkRevoke(true);
          }}
        />
      ) : null}

      {pages.state.error ? (
        <div className={boardPadWide}>
          <Note tone="bad" role="alert">
            Could not load {w.trainees}.{" "}
            <button type="button" className="text-osce-accent hover:text-osce-accent-hover" onClick={() => pages.state.reload()}>
              Retry
            </button>
          </Note>
        </div>
      ) : null}

      {pages.state.loading && !pages.state.data ? (
        <p className="text-osce-body text-osce-ink-500" role="status">
          Loading {w.trainees}…
        </p>
      ) : rows.length === 0 ? (
        query || (w.hiring && allRows.length > 0) ? (
          <div className={boardPadWide}>
            <div className={t.assessMeta}>Search with no match</div>
            <div>{query ? <>No {w.trainees} match &ldquo;{query}&rdquo;.</> : `No ${w.trainees} in this filter.`}</div>
          </div>
        ) : (
          <div className={boardPadWide}>
            <h2 className={h2}>{w.hiring ? CANDIDATES_EMPTY.title : `No ${w.trainees} yet`}</h2>
            <p className={cn(t.assessMeta, "m-0")}>
              {w.hiring ? CANDIDATES_EMPTY.body : `Add ${w.trainees} so you can put them on an exam or training circuit.`}
            </p>
            {canManage ? (
              <button type="button" className={cn(boardBtn("primary"), "self-start")} onClick={onAddPeople}>
                {w.addPeople}
              </button>
            ) : null}
          </div>
        )
      ) : (
        <div role="table" className={card}>
          <div role="row" className={th}>
            {canManage ? <span className="w-4">Select</span> : null}
            <span className="w-8" />
            <span className="flex-[1_1_180px]">{w.hiring ? w.Trainee : "Name"}</span>
            <span className="w-20">{w.YearGroup}</span>
            {w.hiring ? null : <span className="w-[130px]">Programme</span>}
            {w.hiring ? null : <span className="w-[50px]">Sat</span>}
            <span className="w-[170px]">Status</span>
          </div>
          {rows.map((trainee) => {
            const status = traineeStatus(trainee);
            const candidate = candidateStatus(trainee);
            const named = trainee.first_name || trainee.last_name;
            return (
              <div key={trainee.id} role="row" data-testid="trainee-row" className={row}>
                {canManage ? (
                  <input
                    type="checkbox"
                    aria-label={`Select ${displayName(trainee)}`}
                    checked={selected.has(trainee.id)}
                    disabled={bulkBusy}
                    onChange={() => toggle(trainee.id)}
                  />
                ) : null}
                <div aria-hidden className={boardAvatar}>
                  {displayName(trainee).trim().charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0 flex-[1_1_180px]">
                  <div className="font-medium">{named ? displayName(trainee) : trainee.email}</div>
                  {named ? <div className={cn(t.assessMeta, "truncate")}>{trainee.email}</div> : null}
                </div>
                <span className="w-20">{cohortName(cohorts, trainee.cohort_id)}</span>
                {w.hiring ? null : (
                  <span className={cn(t.assessMeta, "w-[130px]")}>
                    {trainee.programme_names?.length ? trainee.programme_names.join(", ") : "No programme"}
                  </span>
                )}
                {w.hiring ? null : <span className="w-[50px] tabular-nums">{trainee.stations_sat}</span>}
                <span className="w-[170px]">
                  {w.hiring ? (
                    <Chip tone={candidate.tone === "ok" ? "ok" : "warn"}>{candidate.label}</Chip>
                  ) : (
                    <Chip tone={status.attention ? "warn" : "ok"}>{`● ${status.attention ?? status.label}`}</Chip>
                  )}
                </span>
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
                    setPending({ kind: accessActive(trainee) ? "revoke" : "restore", trainee });
                  }}
                  onDelete={() => {
                    setError(null);
                    setPending({ kind: "delete", trainee });
                  }}
                  onAnonymise={() => {
                    setError(null);
                    setPending({ kind: "anonymise", trainee });
                  }}
                  onErase={() => setErasing(trainee)}
                />
              </div>
            );
          })}
          {pages.hasMore || pages.moreError ? (
            <div className={cn(row, "justify-center")}>
              <button type="button" className={boardButtonSmall} disabled={pages.loadingMore} onClick={pages.loadMore}>
                {pages.loadingMore ? "Loading…" : "Load more"}
              </button>
              {pages.moreError ? <span className="text-osce-danger-text">{pages.moreError.message}</span> : null}
            </div>
          ) : null}
        </div>
      )}

      {w.hiring && canManage && rows.length > 0 ? <p className={cn(t.assessMeta, "m-0")}>{CANDIDATES_BULK_HINT}</p> : null}

      {!canManage ? (
        <div className={boardPadWide}>
          <div className={t.assessMeta}>{`${w.Supervisor} (read only)`}</div>
          <div>Contact an owner or admin to change who has access.</div>
        </div>
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
              ? deleteLead(named, pending.trainee.stations_sat, w)
              : anonymising
                ? `${named}'s name and email address will be scrubbed and their access revoked. Any decision already recorded about them is kept. This cannot be undone.`
                : revoking
                  ? say(w, `${named} will not be able to sign in or sit anything, and stays on the roster with their results intact.`)
                  : say(w, `${named} will be able to sign in and sit again.`)
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

      <EraseDataDialog
        orgSlug={orgSlug}
        trainee={erasing}
        onClose={() => setErasing(null)}
        onErased={(text) => {
          setErasing(null);
          setNotice({ tone: "success", text });
          pages.state.reload();
          onChanged();
        }}
      />

      <Dialog
        open={confirmingBulkRevoke}
        title={say(w, `Revoke access for ${selectedIds.length} ${selectedIds.length === 1 ? "person" : "people"}?`)}
        lead={say(w, "They will not be able to sign in or sit anything, and stay on the roster with their results intact.")}
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
