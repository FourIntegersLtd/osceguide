"use client";

import { useRouter } from "next/navigation";
import { Alert, AsyncBoundary, Card, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  listMemberships,
  listTrainees,
  rebuildCircuit,
} from "@/domains/assess/api";
import { readConsole, type CircuitConsole } from "@/domains/assess/sessions/api";
import {
  CircuitBuilder,
  type CircuitDraft,
  type PickedStation,
} from "@/domains/assess/CircuitBuilder";
import { editLockNotice } from "@/domains/assess/sessions/support";
import { DEFAULT_BREAK_MINUTES } from "@/domains/assess/timing";

/**
 * Change a circuit that has already been built.
 *
 * A sitting is scheduled weeks ahead and the week arrives with a candidate who
 * has left, a station that turned out to be the wrong version, a circuit that
 * needs a third room. The retiring client had a whole page for this; this port
 * had the run console and nothing else, which made `PUT /circuits/{id}` — served
 * and tested — look like a backend that could not edit a circuit.
 *
 * The slots are rebuilt from scratch, so this is refused as soon as any of them
 * means something: a consultation in progress, a station already sat, feedback
 * recorded. `edit-lock` is asked for on load so the screen can say that before
 * somebody has chosen a new candidate and pressed the button, and the 409 is
 * still shown if the circuit starts in the meantime.
 *
 * Where the console deliberately does not offer a structural edit — adding a
 * latecomer is `append-trainees`, and the clock's own controls are the run
 * screen's business — this is the screen the gap register meant when it wrote
 * "the screen that rebuilds a circuit is where this belongs".
 */
export function EditCircuit({ orgSlug, circuitId }: { orgSlug: string; circuitId: string }) {
  const router = useRouter();
  const { hrefFor } = useSurface();

  const context = useAsync(
    async (signal) => {
      const [console_, trainees, staff] = await Promise.all([
        readConsole(orgSlug, circuitId, signal),
        listTrainees(orgSlug, signal, { accessRevoked: false }),
        listMemberships(orgSlug, signal, { status: "active" }),
      ]);
      return {
        console: console_,
        trainees: trainees.items,
        staff: staff.items.map((member) => ({
          user_id: member.user_id,
          email: member.email,
          role: member.role,
        })),
      };
    },
    [orgSlug, circuitId],
  );

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={context}>
        {({ console: data, trainees, staff }) => {
          const blocked = editLockNotice(data.circuit);
          return (
            <>
              <PageHeader
                title="Edit circuit"
                description={`${data.sitting.name} · ${data.sitting.mode}`}
              />
              <CircuitBuilder
                mode={data.sitting.mode}
                trainees={trainees}
                staff={staff}
                initial={draftFrom(data)}
                submitLabel={blocked ? "Rebuild refused" : "Save changes"}
                disabled={blocked !== null}
                above={
                  blocked ? (
                    <>
                      <Alert tone="warning">{blocked}</Alert>
                      <Card
                        title="What you can still change"
                        description="Name, supervisor and the clock are not part of the lock — only the slots are. The run console changes the clock while a circuit is live."
                      />
                    </>
                  ) : null
                }
                onSubmit={async (shape) => {
                  await rebuildCircuit(orgSlug, circuitId, shape);
                  router.push(hrefFor(`/circuits/${circuitId}`));
                }}
              />
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

/**
 * The circuit's current shape, read off the console.
 *
 * Trainees come back deduplicated rather than one per slot: a training circuit
 * repeats a candidate across the stations they rotate through, and the request
 * wants the people, not the rows. The same goes for stations, which repeat down
 * each column of that rotation.
 */
function draftFrom(console_: CircuitConsole): CircuitDraft {
  const slots = console_.slots ?? [];
  const stations = dedupe(
    slots.flatMap((slot): PickedStation[] =>
      slot.station
        ? [{ version_id: slot.station.version_id, title: slot.station.title ?? "Station" }]
        : [],
    ),
    (station) => station.version_id,
  );
  const people = dedupe(
    slots.flatMap((slot) => (slot.trainee.user_id ? [slot.trainee] : [])),
    (person) => person.user_id ?? "",
  );

  return {
    name: console_.circuit.name,
    stations,
    stationVersionIds: stations.map((station) => station.version_id),
    traineeIds: people.map((person) => person.user_id ?? ""),
    supervisorUserId: console_.circuit.supervisor?.user_id ?? null,
    timing: {
      readingMinutes: console_.circuit.timing?.reading_minutes ?? 2,
      simulationMinutes: console_.circuit.timing?.simulation_minutes ?? 10,
      breakMinutes: console_.circuit.timing?.break_minutes ?? DEFAULT_BREAK_MINUTES,
      breaks: console_.circuit.timing?.breaks ?? [],
    },
  };
}

function dedupe<T>(rows: T[], key: (row: T) => string): T[] {
  const seen = new Set<string>();
  return rows.filter((row) => {
    const id = key(row);
    if (seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}
