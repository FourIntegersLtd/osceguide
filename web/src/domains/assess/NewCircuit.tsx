"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { AsyncBoundary, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { createCircuit, listMemberships, listTrainees, readSitting } from "@/domains/assess/api";
import {
  CircuitBuilder,
  type StaffRow,
  type TraineeRow,
} from "@/domains/assess/CircuitBuilder";

/**
 * Put a circuit on a sitting: who sits it, at which stations, for how long.
 *
 * The backend builds the slots from these two lists, because how they pair
 * depends on the sitting's mode — an exam circuit is one candidate through
 * every station, a training circuit pairs positionally and rotates. Working
 * that out here would be a second implementation of the rule that decides what
 * an examination is.
 *
 * The fields are `CircuitBuilder`, shared with the edit screen: a create and a
 * restructure ask the same four questions, and only the create asks them of an
 * empty circuit.
 */
export function NewCircuit({ orgSlug, sittingId }: { orgSlug: string; sittingId: string }) {
  const router = useRouter();
  const { hrefFor } = useSurface();

  const context = useAsync(
    async (signal) => {
      const [sitting, trainees, staff] = await Promise.all([
        readSitting(orgSlug, sittingId, signal),
        listTrainees(orgSlug, signal, { accessRevoked: false }),
        listMemberships(orgSlug, signal, { status: "active" }),
      ]);
      return {
        sitting,
        trainees: trainees.items,
        staff: staff.items.map((member) => ({
          user_id: member.user_id,
          email: member.email,
          role: member.role,
        })),
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
  const submit = useCallback(
    async (shape: Parameters<typeof createCircuit>[2]) => {
      await createCircuit(orgSlug, sittingId, shape);
      onCreated();
    },
    [orgSlug, sittingId, onCreated],
  );

  return (
    <CircuitBuilder
      mode={mode}
      trainees={trainees}
      staff={staff}
      submitLabel="Create circuit"
      onSubmit={submit}
    />
  );
}
