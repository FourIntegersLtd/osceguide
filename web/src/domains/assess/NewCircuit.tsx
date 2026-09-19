"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, AsyncBoundary, Button, Card, Input, PageHeader, Spinner, cn } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { StationLibrary, type LibraryStation } from "@/capabilities/stations";
import { createCircuit, listMemberships, listTrainees, readSitting } from "@/domains/assess/api";

/**
 * Put a circuit on a sitting: who sits it, at which stations, for how long.
 *
 * The backend builds the slots from these two lists, because how they pair
 * depends on the sitting's mode — an exam circuit is one candidate through
 * every station, a training circuit pairs positionally and rotates. Working
 * that out here would be a second implementation of the rule that decides what
 * an examination is.
 */
export function NewCircuit({ orgSlug, sittingId }: { orgSlug: string; sittingId: string }) {
  const router = useRouter();
  const { hrefFor } = useSurface();

  const context = useAsync(
    async (signal) => {
      const [sitting, trainees, staff] = await Promise.all([
        readSitting(orgSlug, sittingId, signal),
        listTrainees(orgSlug, signal),
        listMemberships(orgSlug, signal),
      ]);
      return {
        sitting,
        trainees: trainees.items.filter((trainee) => !trainee.access_revoked),
        staff: staff.items.filter((member) => member.status !== "revoked"),
      };
    },
    [orgSlug, sittingId],
  );

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={context}>
        {(data) => (
          <>
            <PageHeader
              title="Add a circuit"
              description={`${data.sitting.name} · ${data.sitting.mode}`}
            />
            <Builder
              orgSlug={orgSlug}
              sittingId={sittingId}
              mode={data.sitting.mode}
              trainees={data.trainees}
              staff={data.staff}
              onCreated={() => router.push(hrefFor(`/sittings/${sittingId}`))}
            />
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}

type TraineeRow = {
  id: string;
  user_id: string | null;
  email: string;
  first_name: string | null;
  last_name: string | null;
};
type StaffRow = { user_id: string; email?: string | null; role: string };

function Builder({
  orgSlug,
  sittingId,
  mode,
  trainees,
  staff,
  onCreated,
}: {
  orgSlug: string;
  sittingId: string;
  mode: string;
  trainees: TraineeRow[];
  staff: StaffRow[];
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [stations, setStations] = useState<LibraryStation[]>([]);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [supervisor, setSupervisor] = useState<string>("");
  const [reading, setReading] = useState(2);
  const [simulation, setSimulation] = useState(10);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const isExam = mode === "exam";
  const tooManyStations = isExam && stations.length > 12;

  const submit = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await createCircuit(orgSlug, sittingId, {
        name: name.trim() || "Circuit",
        stationVersionIds: stations.map((station) => station.version_id),
        // `trainee_ids` on the wire means *user* ids: a slot names a user, and
        // an organisation may examine somebody it has not rostered. A trainee
        // who has never signed in has no user row and cannot be put on one.
        traineeIds: [...picked],
        supervisorUserId: supervisor || null,
        timing: { readingMinutes: reading, simulationMinutes: simulation },
      });
      onCreated();
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setBusy(false);
    }
  }, [orgSlug, sittingId, name, stations, picked, supervisor, reading, simulation, onCreated]);

  return (
    <div className="flex flex-col gap-5">
      {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
      {tooManyStations && (
        <Alert tone="warning">An exam circuit takes at most twelve stations.</Alert>
      )}

      <Card title="Details">
        <div className="flex max-w-lg flex-col gap-3">
          <Input
            label="Name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Morning circuit"
          />
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-ink">Supervisor</span>
            <select
              value={supervisor}
              onChange={(event) => setSupervisor(event.target.value)}
              className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink"
            >
              <option value="">Unassigned</option>
              {staff.map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  {member.email ?? member.user_id} ({member.role})
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Reading (minutes)"
              type="number"
              min={0}
              value={reading}
              onChange={(event) => setReading(Number(event.target.value))}
            />
            <Input
              label="Consultation (minutes)"
              type="number"
              min={1}
              value={simulation}
              onChange={(event) => setSimulation(Number(event.target.value))}
            />
          </div>
        </div>
      </Card>

      <Card
        title="Trainees"
        description={
          isExam
            ? "Each candidate goes through every station."
            : "Each trainee is paired with one station, then they rotate."
        }
      >
        {trainees.length === 0 ? (
          <p className="text-sm text-ink-muted">Add trainees to your organisation first.</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {trainees.map((trainee) => {
              const userId = trainee.user_id;
              const on = userId !== null && picked.has(userId);
              const label =
                [trainee.first_name, trainee.last_name].filter(Boolean).join(" ") || trainee.email;
              // Somebody who has never signed in has no user row, and a slot
              // names a user. Saying so beats a foreign key error on submit.
              if (userId === null) {
                return (
                  <li key={trainee.id}>
                    <span
                      title="They have not signed in yet, so they cannot be put on a circuit."
                      className="inline-block cursor-not-allowed rounded-full border border-dashed border-border px-3 py-1.5 text-sm text-ink-subtle"
                    >
                      {label} · not signed in
                    </span>
                  </li>
                );
              }
              return (
                <li key={trainee.id}>
                  <button
                    type="button"
                    aria-pressed={on}
                    onClick={() =>
                      setPicked((current) => {
                        const next = new Set(current);
                        if (next.has(userId)) next.delete(userId);
                        else next.add(userId);
                        return next;
                      })
                    }
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-sm",
                      on
                        ? "border-accent bg-accent text-ink-inverse"
                        : "border-border bg-surface text-ink-muted hover:text-ink",
                    )}
                  >
                    {label}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      <Card title={`Stations (${stations.length})`}>
        <div className="flex flex-col gap-4">
          {stations.length > 0 && (
            <ul className="flex flex-wrap gap-2">
              {stations.map((station) => (
                <li key={station.version_id}>
                  <button
                    type="button"
                    onClick={() =>
                      setStations((current) =>
                        current.filter((item) => item.version_id !== station.version_id),
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
            onPick={(station) =>
              setStations((current) =>
                current.some((item) => item.version_id === station.version_id)
                  ? current
                  : [...current, station],
              )
            }
            pickLabel="Add"
            selectedVersionIds={new Set(stations.map((station) => station.version_id))}
          />
        </div>
      </Card>

      <div className="flex justify-end">
        <Button
          onClick={submit}
          disabled={busy || stations.length === 0 || picked.size === 0 || tooManyStations}
        >
          {busy ? <Spinner label="Creating" /> : "Create circuit"}
        </Button>
      </div>
    </div>
  );
}
