"use client";

import { useMemo, useState } from "react";
import { useAsync } from "@/foundation/hooks";
import { Spinner } from "@/foundation/ui";
import { listTrainees, type Trainee } from "@/domains/assess/api";
import { Dialog } from "@/domains/assess/team/chrome";
import { appendTrainees } from "@/domains/assess/sessions/api";
import type { CircuitConsole } from "@/domains/assess/sessions/api";

/**
 * Somebody who arrived late.
 *
 * Training circuits only — an exam circuit is one candidate by construction,
 * and a second would make its slots mean something else. The new stations are
 * appended to the end and inherit the room that is already open, which is what
 * lets a latecomer join a session that is running rather than watch it.
 */
export function AddTraineesDialog({
  open,
  data,
  orgSlug,
  circuitId,
  busy,
  failure,
  run,
  onClose,
}: {
  open: boolean;
  data: CircuitConsole;
  orgSlug: string;
  circuitId: string;
  busy: string | null;
  failure: string | null;
  run: (name: string, action: () => Promise<unknown>) => Promise<void>;
  onClose: () => void;
}) {
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const roster = useAsync(
    (signal) => (open ? listTrainees(orgSlug, signal) : Promise.resolve(null)),
    [orgSlug, open],
  );

  // A slot names a *user*, so who is already on the circuit is a set of user
  // ids — not of trainee ids, which are a different thing on this backend.
  const alreadyOn = useMemo(
    () => new Set((data.slots ?? []).map((slot) => slot.trainee.user_id)),
    [data.slots],
  );

  /**
   * Somebody who has never signed in has no user row, and a slot names a
   * user — so they cannot be put on a circuit at all. Leaving them out of the
   * list beats a foreign key error on submit.
   */

  const candidates = useMemo(
    () =>
      (roster.data?.items ?? []).filter(
        (trainee) =>
          !trainee.access_revoked && trainee.user_id !== null && !alreadyOn.has(trainee.user_id),
      ),
    [roster.data, alreadyOn],
  );

  if (!open) return null;

  async function commit() {
    await run("append", () => appendTrainees(orgSlug, circuitId, [...picked]));
    setPicked(new Set());
    onClose();
  }

  return (
    <Dialog
      open
      title="Add somebody to this circuit"
      lead="They are given a station at the end of the circuit, in the room that is already open."
      error={failure}
      busy={busy !== null}
      commitLabel={picked.size > 1 ? `Add ${picked.size} people` : "Add them"}
      busyLabel="Adding…"
      commitDisabled={picked.size === 0}
      onClose={onClose}
      onCommit={() => void commit()}
    >
      {roster.loading ? <Spinner /> : null}
      {!roster.loading && candidates.length === 0 ? (
        <p className="text-osce-body text-b2b-mid">
          Everybody on your roster is already on this circuit.
        </p>
      ) : null}
      {candidates.length > 0 ? (
        <ul className="max-h-64 divide-y divide-b2b-border overflow-y-auto rounded-lg border border-b2b-border">
          {candidates.map((trainee) => (
            <li key={trainee.id}>
              <label className="flex cursor-pointer items-center gap-3 px-3 py-2.5 hover:bg-b2b-cream/60">
                <input
                  type="checkbox"
                  checked={picked.has(trainee.user_id ?? "")}
                  onChange={(event) =>
                    setPicked((current) => {
                      const next = new Set(current);
                      const userId = trainee.user_id;
                      if (userId === null) return next;
                      if (event.target.checked) next.add(userId);
                      else next.delete(userId);
                      return next;
                    })
                  }
                  className="h-4 w-4 rounded border-b2b-border text-b2b-accent"
                />
                <span className="min-w-0">
                  <span className="block truncate text-osce-caption font-medium text-b2b-headline">
                    {traineeName(trainee)}
                  </span>
                  <span className="block truncate text-osce-caption text-b2b-mid">
                    {trainee.email}
                  </span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      ) : null}
    </Dialog>
  );
}

function traineeName(trainee: Trainee): string {
  return [trainee.first_name, trainee.last_name].filter(Boolean).join(" ") || trainee.email;
}
