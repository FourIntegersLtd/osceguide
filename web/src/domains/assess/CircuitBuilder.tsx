"use client";

import { useCallback, useMemo, useState } from "react";
import { Alert, Button, Input, Spinner, Panel } from "@/foundation/ui";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import type { StationLibraryScope } from "@/capabilities/stations";
import { useSurface } from "@/capabilities";
import {
  BreakEditor,
  CandidatePicker,
  DefaultBreakInput,
  DurationInputs,
  StationOrder,
  SupervisorSelect,
} from "@/domains/assess/ScheduleSteps";
import type { CircuitShape } from "@/domains/assess/api";
import {
  EMPTY_DRAFT,
  circuitTiming,
  type PickerSet,
  type ScheduleDraft,
  type TraineeRow,
} from "@/domains/assess/scheduleSitting";
import { circuitLeads, isBulkExam } from "@/domains/assess/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";
import {
  DEFAULT_BREAK_MINUTES,
  DEFAULT_READING_MINUTES,
  DEFAULT_SIMULATION_MINUTES,
  MAX_BULK_CANDIDATES,
  MAX_EXAM_CANDIDATES,
  MAX_EXAM_STATIONS,
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
  orgSlug,
  mode,
  trainees,
  staff,
  initial,
  submitLabel,
  onSubmit,
  above,
  disabled = false,
  scope,
  allowManyCandidates = false,
  groups = [],
  cohorts = [],
}: {
  orgSlug: string;
  mode: string;
  trainees: TraineeRow[];
  staff: StaffRow[];
  /** Where an edit starts from. A create leaves it out and gets the defaults. */
  initial?: CircuitDraft;
  submitLabel: string;
  /** `bulk`: several exam candidates, so the caller sends one circuit per candidate. */
  onSubmit: (shape: CircuitShape, bulk: boolean) => Promise<void>;
  /** Anything the caller needs said above the fields: a lock notice, chiefly. */
  above?: React.ReactNode;
  /** True when the caller already knows the submit will be refused: an edit lock, chiefly. */
  disabled?: boolean;
  /** Whose stations the picker offers, and for which exam: the sitting's programme's. */
  scope: StationLibraryScope;
  /**
   * New exam circuits: several candidates make one circuit each. An edit keeps
   * the one-candidate cap because it rebuilds a single circuit.
   */
  allowManyCandidates?: boolean;
  groups?: PickerSet[];
  /** Year groups. */
  cohorts?: PickerSet[];
}) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const [name, setName] = useState(initial?.name ?? "");
  // The same step components the Schedule-a-sitting wizard uses, over the same draft shape.
  const [draft, setDraft] = useState<ScheduleDraft>(() => draftOf(initial, mode));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const patch = useCallback((change: Partial<ScheduleDraft>) => setDraft((current) => ({ ...current, ...change })), []);
  const picked = draft.candidateIds;
  const stations = draft.stations;

  // Only an examination has breaks: `normalise_timing` builds none for any
  // other mode, because a training group rotates without stopping between
  // stations. Offering the control where the server discards the answer is how
  // a save starts to look ignored.
  const isExam = modeSupportsBreaks(mode);
  const candidateCap = allowManyCandidates ? MAX_BULK_CANDIDATES : MAX_EXAM_CANDIDATES;
  // The caller sends several candidates to the bulk route; the name is then a prefix.
  const bulk = allowManyCandidates && isBulkExam(isExam, picked.length);
  const tooManyCandidates = isExam && picked.length > candidateCap;
  const tooManyStations = isExam && stations.length > MAX_EXAM_STATIONS;
  const leads = useMemo(
    () => circuitLeads(staff).map((member) => ({ value: member.user_id, label: `${member.email ?? member.user_id} (${member.role})` })),
    [staff],
  );
  const submit = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await onSubmit(
        {
          name: name.trim() || (bulk ? "Exam" : "Circuit"),
          stationVersionIds: stations.map((station) => station.version_id),
          // `trainee_ids` on the wire means *user* ids: a slot names a user, and
          // an organisation may examine somebody it has not rostered. A trainee
          // who has never signed in has no user row and cannot be put on one.
          traineeIds: picked,
          supervisorUserId: draft.supervisorId || null,
          timing: circuitTiming(draft),
        },
        bulk,
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
      // Stay put. The whole point of the form is the selection somebody has
      // made, and losing it to a 409 is a reason to start the evening again.
      setBusy(false);
    }
  }, [name, draft, stations, picked, isExam, bulk, onSubmit]);

  const submitText = bulk ? `Create ${picked.length} circuits` : submitLabel;
  const prefix = name.trim() || "Exam";

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-ink-muted">
        Used for Edit on an existing circuit and for Add a circuit on a sitting. The Schedule wizard builds the first
        circuits.
      </p>
      {above}
      {error && <Alert tone="danger">{assessErrorMessage(error)}</Alert>}
      {tooManyCandidates && (
        <Alert tone="warning">
          An exam run takes at most {candidateCap} candidates at a time. Deselect {picked.length - candidateCap}.
        </Alert>
      )}
      {tooManyStations && <Alert tone="warning">
          Station {MAX_EXAM_STATIONS + 1} cannot be added: a circuit has at most {MAX_EXAM_STATIONS}.
        </Alert>}

      <Panel title="Details">
        <div className="max-w-lg">
          <Input
            label={bulk ? "Name prefix" : "Name"}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={bulk ? "Exam" : "Morning circuit"}
          />
        </div>
      </Panel>

      <Panel title="Candidates">
        <CandidatePicker
          orgSlug={orgSlug}
          trainees={trainees}
          picked={picked}
          setPicked={(update) => setDraft((current) => ({ ...current, candidateIds: update(current.candidateIds) }))}
          groups={groups}
          yearGroups={cohorts}
          single={isExam}
          words={{ trainee: w.trainee, trainees: w.trainees }}
        />
      </Panel>

      <Panel
        title={`Stations (${stations.length})`}
        description={
          isExam
            ? `At most ${MAX_EXAM_STATIONS} on a formal exam circuit. The picker loads more with Load more.`
            : "The picker loads more with Load more."
        }
      >
        <StationOrder
          stations={stations}
          setStations={(update) => setDraft((current) => ({ ...current, stations: update(current.stations) }))}
          scope={scope}
          examName={scope.examCode ?? "this exam"}
        />
      </Panel>

      <Panel title="Timing">
        <div className="flex max-w-lg flex-col gap-4">
          <DurationInputs draft={draft} patch={patch} />
          {isExam ? (
            <>
              <DefaultBreakInput draft={draft} patch={patch} />
              <BreakEditor draft={draft} patch={patch} />
            </>
          ) : null}
        </div>
      </Panel>

      <Panel title="Supervisor">
        <div className="flex max-w-lg flex-col gap-4">
          <SupervisorSelect draft={draft} patch={patch} leads={leads} inviteHref={hrefFor("/team")} />
        </div>
      </Panel>

      <div className="flex items-center justify-end gap-3">
        {bulk ? (
          <p className="text-sm text-ink-muted">
            {picked.length} candidates make {picked.length} circuits, one each, named {prefix} 1 to {prefix} {picked.length}.
          </p>
        ) : null}
        <Button
          themeType="b2b"
          variant="commit"
          onClick={submit}
          disabled={disabled || busy || stations.length === 0 || picked.length === 0 || tooManyStations || tooManyCandidates}
        >
          {busy ? <Spinner label={submitText} className="text-current" /> : submitText}
        </Button>
      </div>
    </div>
  );
}

/** A circuit's shape as the wizard's draft, so one set of step components edits both. */
function draftOf(initial: CircuitDraft | undefined, mode: string): ScheduleDraft {
  const timing = initial?.timing;
  return {
    ...EMPTY_DRAFT,
    mode: mode === "exam" ? "exam" : "training",
    stations: initial?.stations ?? [],
    candidateIds: initial?.traineeIds ?? [],
    readingMinutes: timing?.readingMinutes ?? DEFAULT_READING_MINUTES,
    consultationMinutes: timing?.simulationMinutes ?? DEFAULT_SIMULATION_MINUTES,
    breakMinutes: timing?.breakMinutes ?? DEFAULT_BREAK_MINUTES,
    breaks: (timing?.breaks ?? []).map((after) => ({
      after,
      minutes: timing?.breakLengths?.[after] ?? timing?.breakMinutes ?? DEFAULT_BREAK_MINUTES,
    })),
    supervisorId: initial?.supervisorUserId ?? "",
  };
}
