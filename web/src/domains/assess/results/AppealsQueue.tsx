"use client";

import { useState } from "react";
import { AsyncBoundary, b2bTokens as t } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { formatShortDateTime } from "@/foundation/format";
import { useSession } from "@/foundation/session";
import { Chip, Note, PeopleDialog as Dialog } from "@/domains/assess/ui";
import { listMemberships } from "@/domains/assess/team/api";
import { useAssessWords } from "@/capabilities/assess-words";
import {
  assignAppeal,
  declineAppeal,
  listAppeals,
  resolveAppeal,
  type Appeal,
} from "@/domains/assess/results/api";
import {
  appealIsLive,
  appealStatusLabel,
  secondMarkerChoices,
} from "@/domains/assess/results/appealsView";
import { OutcomePicker } from "@/domains/assess/results/DecisionParts";
import { outcomeLabel, type AssessmentOutcome } from "@/domains/assess/results/support";
import { boardCard, boardHeadRow, boardInput, boardLabel, boardTab, boardTabs, boardButtonSmall } from "@/foundation/ui/boardKit";

type Action = { kind: "assign" | "decline" | "resolve"; appeal: Appeal } | null;

/**
 * Requests to look at a released result again.
 *
 * A request waits for a second marker, who must not be the person who signed off or released the
 * result; the marker's outcome is appended as a new released revision, never an edit of the old
 * one. Declining needs a reason, which the candidate is sent. The server enforces every rule here;
 * the screen only avoids offering what it will refuse.
 */
export function AppealsQueue({ orgSlug }: { orgSlug: string }) {
  const w = useAssessWords();
  const { session } = useSession();
  const [decided, setDecided] = useState(false);
  const [action, setAction] = useState<Action>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const state = useAsync((signal) => listAppeals(orgSlug, decided, signal), [orgSlug, decided]);
  const me = session?.user.id;

  return (
    <div className="flex flex-col gap-4">
      <div role="tablist" aria-label="Appeals" className={boardTabs}>
        {[
          [false, "Waiting"],
          [true, "Answered"],
        ].map(([value, label]) => (
          <button
            key={String(label)}
            type="button"
            role="tab"
            aria-selected={decided === value}
            className={boardTab(decided === value)}
            onClick={() => setDecided(value as boolean)}
          >
            {label as string}
          </button>
        ))}
      </div>
      {notice ? <Note tone="ok" role="status">{notice}</Note> : null}
      <AsyncBoundary
        state={state}
        isEmpty={(rows) => rows.length === 0}
        empty={{
          title: decided ? "Nothing answered yet." : "No requests waiting.",
          description: `A ${w.trainee} can ask for a released result to be looked at again. Their request appears here.`,
        }}
      >
        {(rows) => (
          <div className={`${boardCard} overflow-hidden`}>
            <div className={boardHeadRow}>
              <span className="flex-[1_1_200px]">{w.Trainee}</span>
              <span className="flex-[2_1_260px]">Reason</span>
              <span className="w-[200px]">Status</span>
              <span className="w-[260px]" />
            </div>
            {rows.map((appeal) => (
              <AppealRow
                key={appeal.id}
                appeal={appeal}
                mine={appeal.assigned_to === me}
                onAct={(kind) => setAction({ kind, appeal })}
              />
            ))}
          </div>
        )}
      </AsyncBoundary>
      <AppealDialog
        orgSlug={orgSlug}
        action={action}
        onClose={() => setAction(null)}
        onDone={(text) => {
          setAction(null);
          setNotice(text);
          state.reload();
        }}
      />
    </div>
  );
}

function AppealRow({
  appeal,
  mine,
  onAct,
}: {
  appeal: Appeal;
  mine: boolean;
  onAct: (kind: "assign" | "decline" | "resolve") => void;
}) {
  const live = appealIsLive(appeal);
  return (
    <div className="flex flex-wrap items-start gap-4 border-t border-osce-border-light px-5 py-4 text-assess-label text-osce-ink-900">
      <span className="flex-[1_1_200px]">
        <b className="block font-medium">{appeal.candidate_name ?? "Candidate"}</b>
        <span className={t.assessMeta}>
          {appeal.sitting_name ?? ""}
          {appeal.original_outcome ? ` · was ${outcomeLabel(appeal.original_outcome)}` : ""}
        </span>
        <span className={`block ${t.assessMeta}`}>
          Asked {formatShortDateTime(appeal.requested_at)}
          {appeal.on_behalf ? " (recorded by staff)" : ""}
        </span>
      </span>
      <span className="flex-[2_1_260px] whitespace-pre-wrap">{appeal.reason}</span>
      <span className="w-[200px]">
        <Chip tone={appeal.status === "declined" ? "neutral" : appeal.status === "resolved" ? "ok" : "warn"}>
          {appealStatusLabel(appeal.status)}
        </Chip>
        {appeal.assigned_to_name ? <span className={`block ${t.assessMeta}`}>{appeal.assigned_to_name}</span> : null}
        {appeal.decision_note ? <span className={`block ${t.assessMeta}`}>{appeal.decision_note}</span> : null}
      </span>
      <span className="flex w-[260px] flex-wrap justify-end gap-2">
        {live && appeal.status === "open" ? (
          <button type="button" className={boardButtonSmall} onClick={() => onAct("assign")}>
            Assign second marker
          </button>
        ) : null}
        {live && appeal.status === "in_review" && mine ? (
          <button type="button" className={boardButtonSmall} onClick={() => onAct("resolve")}>
            Record the new outcome
          </button>
        ) : null}
        {live ? (
          <button type="button" className={boardButtonSmall} onClick={() => onAct("decline")}>
            Decline
          </button>
        ) : null}
      </span>
    </div>
  );
}

/** The one dialog behind all three actions; each asks only what its route needs. */
function AppealDialog({
  orgSlug,
  action,
  onClose,
  onDone,
}: {
  orgSlug: string;
  action: Action;
  onClose: () => void;
  onDone: (text: string) => void;
}) {
  const [assignee, setAssignee] = useState("");
  const [text, setText] = useState("");
  const [outcome, setOutcome] = useState<AssessmentOutcome | "">("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const members = useAsync(
    (signal) => (action?.kind === "assign" ? listMemberships(orgSlug, signal) : Promise.resolve(null)),
    [orgSlug, action?.kind],
  );

  if (!action) return null;
  const { kind, appeal } = action;
  const choices = secondMarkerChoices(members.data?.items ?? [], appeal);
  const ready =
    kind === "assign" ? assignee !== "" : kind === "decline" ? text.trim() !== "" : outcome !== "" && text.trim() !== "";

  async function commit() {
    setBusy(true);
    setError(null);
    try {
      if (kind === "assign") {
        await assignAppeal(orgSlug, appeal.id, assignee);
        onDone("Second marker assigned.");
      } else if (kind === "decline") {
        await declineAppeal(orgSlug, appeal.id, text.trim());
        onDone("Declined. The reason has been sent to the candidate.");
      } else {
        await resolveAppeal(orgSlug, appeal.id, {
          assessmentOutcome: outcome,
          rationale: text.trim(),
          recruitmentOutcome: null,
        });
        onDone("Recorded as a new revision of the result. The candidate has been told.");
      }
      setAssignee("");
      setText("");
      setOutcome("");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open
      title={
        kind === "assign" ? "Assign a second marker" : kind === "decline" ? "Decline this request" : "Record the new outcome"
      }
      lead={
        kind === "assign"
          ? "Choose an administrator who did not sign off or release this result."
          : kind === "decline"
            ? "Say why the result stands. The candidate is sent this."
            : "This is added as a new revision. The earlier revisions stay on record."
      }
      error={error}
      busy={busy}
      commitDisabled={!ready}
      tone={kind === "decline" ? "danger" : "commit"}
      commitLabel={kind === "assign" ? "Assign" : kind === "decline" ? "Decline request" : "Record outcome"}
      busyLabel="Saving…"
      onClose={onClose}
      onCommit={() => void commit()}
    >
      {kind === "assign" ? (
        <div>
          <label htmlFor="appeal-assignee" className={boardLabel}>Second marker</label>
          <select id="appeal-assignee" className={boardInput} value={assignee} onChange={(e) => setAssignee(e.target.value)}>
            <option value="">Choose someone…</option>
            {choices.map((choice) => (
              <option key={choice.userId} value={choice.userId}>{choice.label}</option>
            ))}
          </select>
          {members.data && choices.length === 0 ? (
            <p className={`${t.assessMeta} mt-2`}>
              No other administrator can do this. Add one on the Team page first.
            </p>
          ) : null}
        </div>
      ) : (
        <>
          {kind === "resolve" ? (
            <OutcomePicker value={outcome} disabled={false} onChange={setOutcome} />
          ) : null}
          <div>
            <label htmlFor="appeal-text" className={boardLabel}>
              {kind === "decline" ? "Reason" : "Rationale"}
            </label>
            <textarea
              id="appeal-text"
              className={boardInput}
              rows={4}
              maxLength={4000}
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </div>
        </>
      )}
    </Dialog>
  );
}
