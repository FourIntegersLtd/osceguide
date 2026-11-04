"use client";

import { useCallback, useState } from "react";
import { Alert, Button, Input, Spinner, Panel } from "@/foundation/ui";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import {
  StationLibrary,
  type LibraryStation,
  type StationLibraryScope,
} from "@/capabilities/stations";
import type { CircuitShape } from "@/domains/assess/api";
import { circuitLeads } from "@/domains/assess/support";
import { TraineePicker, type TraineeRow } from "@/domains/assess/TraineePicker";
import { BreaksPanel, DurationFields } from "@/domains/assess/TimingFields";
import {
  DEFAULT_BREAK_MINUTES,
  DEFAULT_READING_MINUTES,
  DEFAULT_SIMULATION_MINUTES,
  clampReadingMinutes,
  MAX_EXAM_CANDIDATES,
  MAX_EXAM_STATIONS,
  clampBreakMinutes,
  clampBreaks,
  pruneBreakLengths,
  modeSupportsBreaks,
} from "@/domains/assess/timing";

/**
 * The one form that decides what a circuit is.
 *
 * Creating a circuit and restructuring one are the same four questions — who,
 * at which stations, for how long, under whom — so there is one builder and two
 * callers. It used to be that only the create existed, which is why "a circuit
 * cannot be corrected after the fact" read as a backend limitation when
 * `PUT /circuits/{id}` had been served all along: there was simply no second
 * caller for the form's own fields.
 *
 * The builder deliberately does not decide anything the backend decides. How a
 * list of trainees and a list of stations become slots is the sitting's *mode*,
 * and re-deriving it here would be a second implementation of the rule that
 * defines what an examination is.
 */

/**
 * Less than a `LibraryStation`.
 *
 * A circuit's own station rows come from the console, which names a station and
 * its version but not the exam it belongs to — so the builder asks only for the
 * two fields it actually reads, and the library satisfies that by being a
 * superset. Inventing an `exam_code` to make one row type fit both callers
 * would be a lie that nothing would catch.
 */
export type PickedStation = { version_id: string; title: string };

export type StaffRow = { user_id: string; email?: string | null; role: string };

/**
 * A `CircuitShape` plus the titles the chips show.
 *
 * What goes *to* the backend is ids only; what a caller starts an edit from also
 * needs the words beside them, which the circuit's own rows already carry.
 */
export interface CircuitDraft extends CircuitShape {
  stations: PickedStation[];
}

export function CircuitBuilder({
  mode,
  trainees,
  staff,
  initial,
  submitLabel,
  onSubmit,
  above,
  disabled = false,
  scope,
}: {
  mode: string;
  trainees: TraineeRow[];
  staff: StaffRow[];
  /** Where an edit starts from. A create leaves it out and gets the defaults. */
  initial?: CircuitDraft;
  submitLabel: string;
  onSubmit: (shape: CircuitShape) => Promise<void>;
  /** Anything the caller needs said above the fields — a lock notice, chiefly. */
  above?: React.ReactNode;
  /** True when the caller already knows the submit will be refused — an edit lock, chiefly. */
  disabled?: boolean;
  /** Whose stations the picker offers, and for which exam: the sitting's programme's. */
  scope: StationLibraryScope;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [stations, setStations] = useState<PickedStation[]>(
    initial?.stations ?? [],
  );
  const [picked, setPicked] = useState<Set<string>>(
    () => new Set(initial?.traineeIds ?? []),
  );
  const [supervisor, setSupervisor] = useState(initial?.supervisorUserId ?? "");
  const [reading, setReading] = useState(
    initial?.timing.readingMinutes ?? DEFAULT_READING_MINUTES,
  );
  const [simulation, setSimulation] = useState(
    initial?.timing.simulationMinutes ?? DEFAULT_SIMULATION_MINUTES,
  );
  const [breakMinutes, setBreakMinutes] = useState(
    initial?.timing.breakMinutes ?? DEFAULT_BREAK_MINUTES,
  );
  const [breaks, setBreaks] = useState<Set<number>>(
    () => new Set(initial?.timing.breaks ?? []),
  );
  const [breakLengths, setBreakLengths] = useState<Record<number, number>>(
    () => ({ ...initial?.timing.breakLengths }),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Only an examination has breaks: `normalise_timing` builds none for any
  // other mode, because a training group rotates without stopping between
  // stations. Offering the control where the server discards the answer is how
  // a save starts to look ignored.
  const isExam = modeSupportsBreaks(mode);
  const candidatesFull = isExam && picked.size >= MAX_EXAM_CANDIDATES;
  const tooManyStations = isExam && stations.length > MAX_EXAM_STATIONS;

  const submit = useCallback(async () => {
    const chosenBreaks = isExam
      ? clampBreaks([...breaks], stations.length)
      : [];
    const defaultBreak = clampBreakMinutes(breakMinutes);
    setBusy(true);
    setError(null);
    try {
      await onSubmit({
        name: name.trim() || "Circuit",
        stationVersionIds: stations.map((station) => station.version_id),
        // `trainee_ids` on the wire means *user* ids: a slot names a user, and
        // an organisation may examine somebody it has not rostered. A trainee
        // who has never signed in has no user row and cannot be put on one.
        traineeIds: [...picked],
        supervisorUserId: supervisor || null,
        timing: {
          readingMinutes: clampReadingMinutes(reading),
          simulationMinutes: simulation,
          // Clamped here as well as on the server: the selection set can hold a
          // position that stopped existing when a station came off the circuit,
          // and a training circuit must not carry breaks at all.
          breakMinutes: defaultBreak,
          breaks: chosenBreaks,
          breakLengths: pruneBreakLengths(
            breakLengths,
            chosenBreaks,
            defaultBreak,
          ),
        },
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
      // Stay put. The whole point of the form is the selection somebody has
      // made, and losing it to a 409 is a reason to start the evening again.
      setBusy(false);
    }
  }, [
    name,
    stations,
    picked,
    supervisor,
    reading,
    simulation,
    breakMinutes,
    breaks,
    breakLengths,
    isExam,
    onSubmit,
  ]);

  return (
    <div className="flex flex-col gap-5">
      {above}
      {error && <Alert tone="danger">{assessErrorMessage(error)}</Alert>}
      {tooManyStations && (
        <Alert tone="warning">
          An exam circuit takes at most {MAX_EXAM_STATIONS} stations.
        </Alert>
      )}

      <Panel title="Details">
        <div className="flex max-w-lg flex-col gap-3">
          <Input
            label="Name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Morning circuit"
          />
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-ink">Lead</span>
            <select
              value={supervisor}
              onChange={(event) => setSupervisor(event.target.value)}
              className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink"
            >
              <option value="">Unassigned</option>
              {circuitLeads(staff).map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  {member.email ?? member.user_id} ({member.role})
                </option>
              ))}
            </select>
          </label>
          <DurationFields
            reading={reading}
            setReading={setReading}
            simulation={simulation}
            setSimulation={setSimulation}
          />
        </div>
      </Panel>

      {isExam ? (
        <BreaksPanel
          stationCount={stations.length}
          breakMinutes={breakMinutes}
          setBreakMinutes={setBreakMinutes}
          breaks={breaks}
          setBreaks={setBreaks}
          breakLengths={breakLengths}
          setBreakLengths={setBreakLengths}
        />
      ) : null}

      <TraineePicker
        trainees={trainees}
        picked={picked}
        setPicked={setPicked}
        isExam={isExam}
        candidatesFull={candidatesFull}
      />

      <Panel title={`Stations (${stations.length})`}>
        <div className="flex flex-col gap-4">
          {stations.length > 0 && (
            <ul className="flex flex-wrap gap-2">
              {stations.map((station) => (
                <li key={station.version_id}>
                  <button
                    type="button"
                    onClick={() =>
                      setStations((current) =>
                        current.filter(
                          (item) => item.version_id !== station.version_id,
                        ),
                      )
                    }
                    className="rounded-full border border-border px-3 py-1 text-sm text-ink-muted hover:border-danger hover:text-danger"
                  >
                    {station.title} ×
                  </button>
                </li>
              ))}
            </ul>
          )}
          <StationLibrary
            scope={scope}
            onPick={(station: LibraryStation) =>
              setStations((current) =>
                current.some((item) => item.version_id === station.version_id)
                  ? current
                  : [
                      ...current,
                      { version_id: station.version_id, title: station.title },
                    ],
              )
            }
            pickLabel="Add"
            selectedVersionIds={
              new Set(stations.map((station) => station.version_id))
            }
          />
        </div>
      </Panel>

      <div className="flex justify-end">
        <Button
          themeType="b2b"
          variant="commit"
          onClick={submit}
          disabled={
            disabled ||
            busy ||
            stations.length === 0 ||
            picked.size === 0 ||
            tooManyStations
          }
        >
          {busy ? (
            <Spinner label={submitLabel} className="text-current" />
          ) : (
            submitLabel
          )}
        </Button>
      </div>
    </div>
  );
}
