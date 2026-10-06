"use client";

import { Button } from "@/foundation/ui";
import type { Trainee } from "@/domains/assess/api";
import {
  accessActive,
  invitationNotAccepted,
  invitationResendable,
} from "@/domains/assess/roster/support";

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
  if (!canManage) return null;

  /* A row the migration left with no account behind it has never been invited
     at all, and the backend treats this as a first invitation rather than a
     refusal — so the button says which of the two it is about to send. */
  const inviteLabel = invitationNotAccepted(trainee) ? "Send invitation" : "Resend invitation";

  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <Button
        themeType="b2b"
        variant="secondary"
        size="sm"
        title="Change their name, email or cohort."
        onClick={onEdit}
      >
        Edit
      </Button>
      {invitationResendable(trainee) ? (
        invitationSettled ? (
          <Button
            themeType="b2b"
            variant="secondary"
            size="sm"
            disabled
            title="That person has already set up their account, so there is no invitation to resend."
          >
            Already joined
          </Button>
        ) : (
          <Button
            themeType="b2b"
            variant="secondary"
            size="sm"
            disabled={busy}
            title="Email them a fresh link to set up their account."
            onClick={onResend}
          >
            {busy ? "Sending…" : inviteLabel}
          </Button>
        )
      ) : null}
      <Button
        themeType="b2b"
        variant="secondary"
        size="sm"
        title={
          accessActive(trainee)
            ? "Stop them sitting or signing in. Their records are kept."
            : "Let them sit and sign in again."
        }
        onClick={onAccess}
      >
        {accessActive(trainee) ? "Revoke" : "Restore"}
      </Button>
      <Button
        themeType="b2b"
        variant="danger"
        size="sm"
        title="Remove them from the roster. Refused once a result is decided."
        onClick={onDelete}
      >
        Delete
      </Button>
      {trainee.anonymised ? (
        <Button themeType="b2b" variant="secondary" size="sm" disabled title="Already anonymised">
          Anonymised
        </Button>
      ) : (
        <Button
          themeType="b2b"
          variant="secondary"
          size="sm"
          title="Erase their personal details but keep the results."
          onClick={onAnonymise}
        >
          Anonymise
        </Button>
      )}
    </div>
  );
}
