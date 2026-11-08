"use client";

import { say } from "@/domains/assess/roster/rosterWords";
import { useAssessWords } from "@/capabilities/assess-words";
import { LuBan, LuPencil, LuRotateCcw, LuSend, LuTrash2, LuUserX } from "react-icons/lu";
import type { Trainee } from "@/domains/assess/api";
import { accessActive, displayName, invitationResendable, traineeActionLabels } from "@/domains/assess/roster/support";
import { ActionMenu, type ActionMenuItem } from "@/foundation/ui";

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
}) {
  const w = useAssessWords();
  if (!canManage) return null;
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
    {
      label: "Delete",
      icon: <LuTrash2 className={ICON} />,
      tone: "danger",
      hint: "Remove them from your list. You cannot do this once they have a result; revoke their access instead.",
      onSelect: onDelete,
    },
  );
  return <ActionMenu label={`Actions for ${displayName(trainee)}`} items={items} />;
}
