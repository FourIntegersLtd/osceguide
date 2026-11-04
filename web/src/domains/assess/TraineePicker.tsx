"use client";

import { useState, type Dispatch, type SetStateAction } from "react";
import { Input, Panel, cn } from "@/foundation/ui";
import { expandToUsers, groupNotice, toggleInSet } from "@/domains/assess/support";

export type TraineeRow = {
  id: string;
  user_id: string | null;
  email: string;
  first_name: string | null;
  last_name: string | null;
  cohort_id?: string | null;
};

/** A named set of roster ids the picker can tick in one go. */
export type PickerSet = { id: string; label: string; loadMemberIds: () => Promise<string[]> };

/** Who sits a circuit: the organisation's signed-in trainees, searchable, picked by user id. */
export function TraineePicker({
  trainees,
  picked,
  setPicked,
  isExam,
  candidatesFull,
  groups = [],
  cohorts = [],
}: {
  trainees: TraineeRow[];
  picked: Set<string>;
  setPicked: Dispatch<SetStateAction<Set<string>>>;
  isExam: boolean;
  candidatesFull: boolean;
  /** Groups and cohorts offered as "Add a ..." shortcuts; leave empty to hide them. */
  groups?: PickerSet[];
  cohorts?: PickerSet[];
}) {
  const [traineeSearch, setTraineeSearch] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const addSet = async (set: PickerSet | undefined) => {
    if (!set) return;
    try {
      const result = expandToUsers(await set.loadMemberIds(), trainees);
      setPicked((current) => new Set([...current, ...result.userIds]));
      setNotice(groupNotice(result));
    } catch {
      setNotice(`Could not load ${set.label}. Try again.`);
    }
  };
  return (
    <Panel
      title="Trainees"
      description={`${picked.size} of ${trainees.length} selected. ${
        isExam
          ? "An exam circuit is one candidate's sitting: they go through every station."
          : "Each trainee is paired with one station, then they rotate."
      }`}
    >
      {trainees.length === 0 ? (
        <p className="text-sm text-ink-muted">
          Add trainees to your organisation first.
        </p>
      ) : (
        <>
          <div className="mb-3 flex flex-wrap gap-3">
            {[
              { label: "Add a group", noun: "group", sets: groups },
              { label: "Add a cohort", noun: "cohort", sets: cohorts },
            ]
              .filter((picker) => picker.sets.length > 0)
              .map((picker) => (
                <label key={picker.noun} className="flex flex-col gap-1.5">
                  <span className="text-sm font-medium text-ink">{picker.label}</span>
                  <select
                    value=""
                    onChange={(event) =>
                      void addSet(picker.sets.find((set) => set.id === event.target.value))
                    }
                    className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink"
                  >
                    <option value="">Add a {picker.noun}…</option>
                    {picker.sets.map((set) => (
                      <option key={set.id} value={set.id}>
                        {set.label}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
          </div>
          {notice && (
            <p role="status" className="mb-3 text-sm text-ink-muted">
              {notice}
            </p>
          )}
          <div className="mb-3 max-w-sm">
            <Input
              label="Find a trainee"
              value={traineeSearch}
              onChange={(event) => setTraineeSearch(event.target.value)}
            />
          </div>
          <ul className="flex flex-wrap gap-2">
            {trainees
              .filter((trainee) =>
                `${trainee.first_name ?? ""} ${trainee.last_name ?? ""} ${trainee.email}`
                  .toLowerCase()
                  .includes(traineeSearch.trim().toLowerCase()),
              )
              .map((trainee) => {
                const userId = trainee.user_id;
                const on = userId !== null && picked.has(userId);
                const label =
                  [trainee.first_name, trainee.last_name]
                    .filter(Boolean)
                    .join(" ") || trainee.email;
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
                      disabled={!on && candidatesFull}
                      title={
                        !on && candidatesFull
                          ? "An exam circuit is one candidate's sitting. Deselect the current candidate to pick another."
                          : undefined
                      }
                      onClick={() => setPicked((current) => toggleInSet(current, userId))}
                      className={cn(
                        "rounded-full border px-3 py-1.5 text-sm",
                        on
                          ? "border-b2b-headline bg-b2b-headline text-ink-inverse"
                          : "border-b2b-border bg-b2b-surface text-b2b-mid hover:text-b2b-headline",
                      )}
                    >
                      {label}
                    </button>
                  </li>
                );
              })}
          </ul>
        </>
      )}
    </Panel>
  );
}
