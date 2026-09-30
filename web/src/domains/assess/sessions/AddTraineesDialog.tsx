"use client";

import { useMemo, useState } from "react";
import { useAsync } from "@/foundation/hooks";
import { Spinner } from "@/foundation/ui";
import { hasCode } from "@/foundation/platform-client";
import { listTrainees, type Trainee } from "@/domains/assess/api";
import { Dialog } from "@/domains/assess/team/chrome";
import { appendTrainees } from "@/domains/assess/sessions/api";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";

/**
 * Somebody who arrived late.
 *
 * Training circuits only — an exam circuit is one candidate by construction,
 * and a second would make its slots mean something else. The new stations are
 * appended to the end and inherit the room that is already open, which is what
 * lets a latecomer join a session that is running rather than watch it.
 *
 * Each arrival is pointed at a station. The retiring dialog made you name one
 * per person; this backend will also place them itself, at the station the
 * circuit is already running, so that is the default and naming one is the
 * opt-in. The choice is limited to stations already on this circuit on purpose:
 * a station nobody here is sitting is not a latecomer's destination, it is a
 * different circuit, and that edit belongs to the circuit builder.
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
  const [station, setStation] = useState<string>("");
  const [refusal, setRefusal] = useState<string | null>(null);
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

  const stations = useMemo(() => stationChoices(data.slots ?? []), [data.slots]);

  /* Each opening is a fresh question, not a continuation of the last one that
   * was refused — so the runner mounts this only while it is open and the
   * picks, the station and a refusal go away with it. Clearing them from an
   * effect would be a second render for a state the mount already has.
   */
  if (!open) return null;

  async function commit() {
    setRefusal(null);
    const arrivals = [...picked];
    // Positional against the arrivals, which is the pairing the server expects:
    // one station named for each person, or none named at all.
    const target = station ? arrivals.map(() => station) : undefined;
    let added = false;
    await run("append", async () => {
      try {
        await appendTrainees(orgSlug, circuitId, arrivals, target);
        added = true;
      } catch (cause) {
        setRefusal(refusalFor(cause));
      }
    });
    if (!added) return;
    setPicked(new Set());
    setStation("");
    onClose();
  }

  return (
    <Dialog
      open
      title="Add somebody to this circuit"
      lead="They are given a station at the end of the circuit, in the room that is already open."
      error={refusal ?? failure}
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

      {picked.size > 0 ? (
        <label className="flex flex-col gap-1.5">
          <span className="text-osce-caption font-medium text-b2b-headline">Station</span>
          <select
            value={station}
            onChange={(event) => {
              setStation(event.target.value);
              setRefusal(null);
            }}
            className="h-10 w-full rounded-lg border border-b2b-border bg-white px-3 text-osce-body text-b2b-headline"
          >
            <option value="">The station this circuit is running</option>
            {stations.map((choice) => (
              <option key={choice.versionId} value={choice.versionId}>
                {choice.label}
              </option>
            ))}
          </select>
          <span className="text-osce-caption text-b2b-mid">
            {picked.size > 1
              ? "Each of them goes to the station chosen here, at the end of the circuit. Rebuild the circuit to spread them across it."
              : "Their turn is appended after everything already on the circuit."}
          </span>
        </label>
      ) : null}
    </Dialog>
  );
}

/**
 * The stations this circuit already runs, deduped and in slot order.
 *
 * The list is what the server will accept: a version nobody on this circuit is
 * sitting is answered with `station_not_on_circuit`, so offering one would be
 * offering a refusal.
 */
function stationChoices(slots: ConsoleSlot[]): { versionId: string; label: string }[] {
  const seen = new Map<string, string>();
  for (const slot of slots) {
    const station = slot.station;
    if (seen.has(station.version_id)) continue;
    const title = station.title?.trim() || "Untitled station";
    seen.set(station.version_id, station.version ? `${title} · v${station.version}` : title);
  }
  return [...seen].map(([versionId, label]) => ({ versionId, label }));
}

/**
 * A refusal, said the way this dialog can act on.
 *
 * Branching on the code, never on the sentence — but the two new ones keep the
 * server's own words underneath, because they name the ids at fault and that is
 * more use to a supervisor than a paraphrase.
 */
function refusalFor(cause: unknown): string {
  const message = cause instanceof Error ? cause.message : String(cause);
  if (hasCode(cause, "trainee_already_on_circuit")) {
    return `Already on this circuit, so nothing was added. ${message}`;
  }
  if (hasCode(cause, "station_not_on_circuit")) {
    return `That station is not on this circuit — pick one from the list, or leave it to the station being run. ${message}`;
  }
  if (hasCode(cause, "not_permitted_in_mode")) {
    return "An examination cannot take a late arrival: it is one candidate through every station.";
  }
  return message;
}

function traineeName(trainee: Trainee): string {
  return [trainee.first_name, trainee.last_name].filter(Boolean).join(" ") || trainee.email;
}
