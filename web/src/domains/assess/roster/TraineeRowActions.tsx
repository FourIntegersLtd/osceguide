"use client";

import { LuBan, LuEraser, LuPencil, LuRotateCcw, LuSend, LuTrash2, LuUserX } from "react-icons/lu";
import type { Trainee } from "@/domains/assess/api";
import { say } from "@/domains/assess/roster/rosterWords";
import { useAssessWords } from "@/capabilities/assess-words";
import {
  accessActive,
  displayName,
  invitationNotAccepted,
  invitationResendable,
  traineeActionLabels,
} from "@/domains/assess/roster/support";
import { ActionMenu, type ActionMenuItem } from "@/foundation/ui";
import { boardBtn, boardButtonSmall } from "@/foundation/ui/boardKit";

const ICON = "h-4 w-4";

/**
 * The per-row controls, kept out of the table's column list so the table stays
 * a description of columns.
 *
 * `invitationSettled` is what the screen knows about the invitation and nothing
 * else: `TraineeRead` carries no acceptance field, so the button is offered and
 * the backend's `invitation_not_pending` is what retires it. A frontend that
 * guessed it already knew would be back to the retiring client's habit of
 * offering actions the API then refused.
 */
export function TraineeRowActions({
  trainee,
  invitationSettled,
  canManage,
  busy = false,
  onEdit,
  onResend,
  onAccess,
  onDelete,
  onAnonymise,
  onErase,
}: {
  trainee: Trainee;
  invitationSettled: boolean;
  canManage: boolean;
  /** This row's re-send is in flight; the rest of the row keeps its buttons. */
  busy?: boolean;
  onEdit: () => void;
  onResend: () => void;
  onAccess: () => void;
  /** Offered on every row; the backend is what actually refuses a decided one. */
  onDelete: () => void;
  /** The GDPR path `onDelete` refuses to — always available, never destroys anything. */
  onAnonymise: () => void;
  /** Opens the typed-confirmation dialog; the removal itself cannot be undone. */
  onErase: () => void;
}) {
  const w = useAssessWords();
  if (!canManage) return null;

  // A hire workspace gets one menu per row; an institution keeps its visible buttons.
  if (w.hiring) {
    const labels = traineeActionLabels(trainee);
    const active = accessActive(trainee);
    const items: ActionMenuItem[] = [
      { label: "Edit", icon: <LuPencil className={ICON} />, hint: say(w, "Change their name, email or year group."), onSelect: onEdit },
    ];
    if (invitationResendable(trainee)) {
      items.push({
        label: invitationSettled ? "Already joined" : labels.invite,
        icon: <LuSend className={ICON} />,
        hint: invitationSettled
          ? say(w, "That person has already set up their account, so there is no invitation to resend.")
          : busy
            ? "Sending..."
            : "Email them a fresh link to set up their account.",
        disabled: invitationSettled || busy,
        onSelect: onResend,
      });
    }
    items.push(
      {
        label: labels.access,
        icon: active ? <LuBan className={ICON} /> : <LuRotateCcw className={ICON} />,
        hint: say(w, active ? "Stop them sitting or signing in. Their records are kept." : "Let them sit and sign in again."),
        onSelect: onAccess,
      },
      {
        label: trainee.anonymised ? "Anonymised" : "Anonymise",
        icon: <LuUserX className={ICON} />,
        hint: trainee.anonymised ? "Already anonymised" : "Erase their personal details but keep the results.",
        disabled: trainee.anonymised,
        onSelect: onAnonymise,
      },
    );
    if (!trainee.anonymised) {
      items.push({
        label: "Delete data",
        icon: <LuEraser className={ICON} />,
        tone: "danger",
        hint: "Permanently remove their transcripts and personal details. Marks are kept, anonymised.",
        onSelect: onErase,
      });
    }
    items.push({
      label: "Delete",
      icon: <LuTrash2 className={ICON} />,
      tone: "danger",
      hint: "Remove them from your list. You cannot do this once they have a result; revoke their access instead.",
      onSelect: onDelete,
    });
    return <ActionMenu label={`Actions for ${displayName(trainee)}`} items={items} />;
  }

  /* A row the migration left with no account behind it has never been invited
     at all, and the backend treats this as a first invitation rather than a
     refusal — so the button says which of the two it is about to send. */
  const inviteLabel = invitationNotAccepted(trainee) ? "Send invitation" : "Resend invitation";

  return (
    <div className="flex flex-[1_1_100%] flex-wrap items-center justify-end gap-2.5">
      <button type="button" className={boardButtonSmall}
        title="Change their name, email or cohort."
        onClick={onEdit}
      >
        Edit
      </button>
      {invitationResendable(trainee) ? (
        invitationSettled ? (
          <button type="button" className={boardButtonSmall}
            disabled
            title="That person has already set up their account, so there is no invitation to resend."
          >
            Already joined
          </button>
        ) : (
          <button type="button" className={boardButtonSmall}
            disabled={busy}
            title="Email them a fresh link to set up their account."
            onClick={onResend}
          >
            {busy ? "Sending…" : inviteLabel}
          </button>
        )
      ) : null}
      <button type="button" className={boardButtonSmall}
        title={
          accessActive(trainee)
            ? "Stop them sitting or signing in. Their records are kept."
            : "Let them sit and sign in again."
        }
        onClick={onAccess}
      >
        {accessActive(trainee) ? "Revoke" : "Restore"}
      </button>
      <button type="button" className={boardBtn("danger", true)}
        title="Remove them from the roster. Refused once a result is decided."
        onClick={onDelete}
      >
        Delete
      </button>
      {trainee.anonymised ? (
        <button type="button" className={boardButtonSmall} disabled title="Already anonymised">
          Anonymised
        </button>
      ) : (
        <button type="button" className={boardButtonSmall}
          title="Erase their personal details but keep the results."
          onClick={onAnonymise}
        >
          Anonymise
        </button>
      )}
      {trainee.anonymised ? null : (
        <button type="button" className={boardBtn("danger", true)}
          title="Permanently remove their transcripts and personal details. Marks are kept, anonymised."
          onClick={onErase}
        >
          Delete data
        </button>
      )}
    </div>
  );
}
