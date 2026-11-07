"use client";

import { useState } from "react";
import { PeopleDialog as Dialog } from "@/domains/assess/ui";
import type { Trainee } from "@/domains/assess/api";
import { errorMessage } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { eraseCandidateData } from "@/domains/assess/roster/api";
import { displayName } from "@/domains/assess/roster/support";
import { erasureConfirmed } from "@/domains/assess/roster/support";
import { boardInput, boardLabel } from "@/foundation/ui/boardKit";

/**
 * The irreversible removal of a candidate's recordings, transcripts and personal details.
 *
 * It stays disabled until the candidate's own address is typed, so a stray click cannot start it.
 * What is kept is stated before the button, not after: marks and the result ledger remain, with
 * no name attached.
 */
export function EraseDataDialog({
  orgSlug,
  trainee,
  onClose,
  onErased,
}: {
  orgSlug: string;
  trainee: Trainee | null;
  onClose: () => void;
  onErased: (text: string) => void;
}) {
  const { session } = useSession();
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allowed = can(session, "sign_off_results");
  if (!trainee || !allowed) return null;
  const named = displayName(trainee);

  function close() {
    setTyped("");
    setError(null);
    onClose();
  }

  async function commit() {
    if (!trainee) return;
    setBusy(true);
    setError(null);
    try {
      await eraseCandidateData(orgSlug, trainee.id, typed);
      setTyped("");
      onErased(`${named}'s transcripts and personal details have been permanently removed. Their marks are kept without a name.`);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open
      title={`Delete ${named}'s data?`}
      lead="This permanently removes their transcripts, name, email address and the notes written about them. Their marks and the record of results stay, with no name attached. This cannot be undone."
      error={error}
      busy={busy}
      tone="danger"
      commitDisabled={!erasureConfirmed(typed, trainee.email)}
      commitLabel="Delete their data"
      busyLabel="Deleting…"
      onClose={close}
      onCommit={() => void commit()}
    >
      <div>
        <label htmlFor="erase-confirmation" className={boardLabel}>
          {`Type ${trainee.email} to confirm`}
        </label>
        <input
          id="erase-confirmation"
          className={boardInput}
          autoComplete="off"
          value={typed}
          onChange={(event) => setTyped(event.target.value)}
        />
      </div>
    </Dialog>
  );
}
