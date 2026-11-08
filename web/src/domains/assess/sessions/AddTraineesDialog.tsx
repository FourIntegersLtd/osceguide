"use client";

import { useAssessWords, type AssessWords } from "@/capabilities/assess-words";
import { useMemo, useState } from "react";
import { useAsync } from "@/foundation/hooks";
import { AsyncBoundary } from "@/foundation/ui";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import { hasCode } from "@/foundation/platform-client";
import { listActiveTrainees, type Trainee } from "@/domains/assess/api";
import { latecomerChoices } from "@/domains/assess/sessions/latecomers";
import { PeopleDialog } from "@/domains/assess/ui";
import { assessHelper } from "@/foundation/ui/b2bTokens";
import { appendTrainees } from "@/domains/assess/sessions/api";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import { boardInput, boardLabel } from "@/foundation/ui/boardKit";

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
  offline,
  failure,
  run,
  onClose,
}: {
  open: boolean;
  data: CircuitConsole;
  orgSlug: string;
  circuitId: string;
  busy: string | null;
  /** The live stream is down, so the roster on screen may be stale. */
  offline: boolean;
  failure: string | null;
  run: (name: string, action: () => Promise<unknown>) => Promise<void>;
  onClose: () => void;
}) {
  const w = useAssessWords();
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [station, setStation] = useState<string>("");
  const [refusal, setRefusal] = useState<string | null>(null);
  const roster = useAsync(
    (signal) => (open ? listActiveTrainees(orgSlug, signal) : Promise.resolve(null)),
    [orgSlug, open],
  );

  const candidates = useMemo(
    () => latecomerChoices(roster.data ?? [], data.slots ?? []),
    [roster.data, data.slots],
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
        setRefusal(refusalFor(cause, w));
      }
    });
    if (!added) return;
    setPicked(new Set());
    setStation("");
    onClose();
  }

  return (
    <PeopleDialog
      open
      title={`Add somebody to this ${w.circuit}`}
      lead={`They are given a station at the end of the ${w.circuit}, in the room that is already open.`}
      error={refusal ?? failure}
      busy={busy !== null || offline}
      commitLabel={picked.size > 1 ? `Add ${picked.size} people` : "Add them"}
      busyLabel="Adding…"
      commitDisabled={picked.size === 0}
      onClose={onClose}
      onCommit={() => void commit()}
    >
      <AsyncBoundary state={roster}>
        {() =>
          candidates.length === 0 ? (
            <p className={assessHelper}>{`Everybody on your roster is already on this ${w.circuit}.`}</p>
          ) : (
            <div className="flex max-h-64 flex-col overflow-y-auto">
              {candidates.map(({ trainee, refusal: notYet }) => (
                <label
                  key={trainee.id}
                  className={`flex min-h-8 items-start gap-2.5 text-assess-label font-normal ${notYet ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
                >
                  <input
                    type="checkbox"
                    disabled={notYet !== null}
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
                    className="mt-0.5 h-4 w-4 rounded border-osce-border text-osce-accent"
                  />
                  {`${traineeName(trainee)} · ${notYet ?? trainee.email}`}
                </label>
              ))}
            </div>
          )
        }
      </AsyncBoundary>

        <div>
          <label htmlFor="late-station" className={boardLabel}>Station</label>
          <select
            id="late-station"
            value={station}
            onChange={(event) => {
              setStation(event.target.value);
              setRefusal(null);
            }}
            className={boardInput}
          >
            <option value="">{`The station this ${w.circuit} is running`}</option>
            {stations.map((choice) => (
              <option key={choice.versionId} value={choice.versionId}>
                {choice.label}
              </option>
            ))}
          </select>
          <div className={`${assessHelper} mt-1.5`}>
            {picked.size > 1
              ? `Everyone you add takes the station chosen here, after everyone else on the ${w.circuit}. To spread them across different stations, rebuild the ${w.circuit}.`
              : `They take their turn after everyone already on the ${w.circuit}.`}
          </div>
        </div>

    </PeopleDialog>
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
function refusalFor(cause: unknown, w: AssessWords): string {
  const circuit = w.circuit;
  const message = cause instanceof Error ? cause.message : String(cause);
  if (hasCode(cause, "trainee_already_on_circuit")) {
    return `Already on this ${circuit}, so nothing was added. ${message}`;
  }
  if (hasCode(cause, "station_not_on_circuit")) {
    return `That station is not on this ${circuit}. Pick one from the list, or leave it to the station being run. ${message}`;
  }
  if (hasCode(cause, "not_permitted_in_mode")) {
    return "An examination cannot take a late arrival: it is one candidate through every station.";
  }
  return assessErrorMessage(cause, w);
}

function traineeName(trainee: Trainee): string {
  return [trainee.first_name, trainee.last_name].filter(Boolean).join(" ") || trainee.email;
}
