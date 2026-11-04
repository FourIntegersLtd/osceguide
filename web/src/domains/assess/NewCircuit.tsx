"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { AsyncBoundary, B2CPageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import type { StationLibraryScope } from "@/capabilities/stations";
import { useSurface } from "@/capabilities";
import {
  createCircuit,
  createExamCircuits,
  listActiveMembers,
  listActiveTrainees,
  readSitting,
  sittingLibraryScope,
  timingBody,
} from "@/domains/assess/api";
import { CircuitBuilder, type StaffRow } from "@/domains/assess/CircuitBuilder";
import {
  readAllCohorts,
  readAllTraineeGroups,
  readGroupMembers,
} from "@/domains/assess/roster/api";
import type { PickerSet, TraineeRow } from "@/domains/assess/TraineePicker";

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
export function NewCircuit({
  orgSlug,
  sittingId,
}: {
  orgSlug: string;
  sittingId: string;
}) {
  const router = useRouter();
  const { hrefFor } = useSurface();

  const context = useAsync(
    async (signal) => {
      const [sitting, trainees, staff, groupPage, cohortPage] =
        await Promise.all([
          readSitting(orgSlug, sittingId, signal),
          listActiveTrainees(orgSlug, signal),
          listActiveMembers(orgSlug, signal),
          readAllTraineeGroups(orgSlug, signal),
          readAllCohorts(orgSlug, signal),
        ]);
      const groups: PickerSet[] = groupPage.map((group) => ({
        id: group.id,
        label: group.label,
        loadMemberIds: () => readGroupMembers(orgSlug, group.id, signal),
      }));
      // The api has no cohort filter, so a cohort's members are the loaded trainees tagged with it.
      const cohorts: PickerSet[] = cohortPage.map((cohort) => ({
        id: cohort.id,
        label: cohort.name,
        loadMemberIds: async () =>
          trainees.filter((t) => t.cohort_id === cohort.id).map((t) => t.id),
      }));
      return {
        groups,
        cohorts,
        sitting,
        scope: await sittingLibraryScope(orgSlug, sitting, signal),
        trainees,
        staff: staff.map((member) => ({
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
            <B2CPageHeader
              back={{
                href: hrefFor(`/sittings/${sittingId}`),
                label: data.sitting.name,
              }}
              title="Add a circuit"
              subtitle={`${data.sitting.name} · ${data.sitting.mode}`}
            />
            <Builder
              orgSlug={orgSlug}
              sittingId={sittingId}
              mode={data.sitting.mode}
              scope={data.scope}
              trainees={data.trainees}
              groups={data.groups}
              cohorts={data.cohorts}
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
  scope,
  trainees,
  groups,
  cohorts,
  staff,
  onCreated,
}: {
  orgSlug: string;
  sittingId: string;
  mode: string;
  scope: StationLibraryScope;
  trainees: TraineeRow[];
  groups: PickerSet[];
  cohorts: PickerSet[];
  staff: StaffRow[];
  onCreated: () => void;
}) {
  const submit = useCallback(
    async (shape: Parameters<typeof createCircuit>[2], bulk: boolean) => {
      if (bulk) {
        await createExamCircuits(orgSlug, sittingId, {
          name_prefix: shape.name,
          candidate_user_ids: shape.traineeIds,
          station_version_ids: shape.stationVersionIds,
          supervisor_user_id: shape.supervisorUserId,
          timing: timingBody(shape.timing),
        });
      } else {
        await createCircuit(orgSlug, sittingId, shape);
      }
      onCreated();
    },
    [orgSlug, sittingId, onCreated],
  );

  return (
    <CircuitBuilder
      mode={mode}
      scope={scope}
      trainees={trainees}
      groups={groups}
      cohorts={cohorts}
      allowManyCandidates
      staff={staff}
      submitLabel="Create circuit"
      onSubmit={submit}
    />
  );
}
