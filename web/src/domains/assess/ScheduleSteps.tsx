"use client";

import { useState } from "react";
import Link from "next/link";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { HiOutlineArrowDown, HiOutlineArrowUp, HiOutlineBars3, HiOutlineTrash } from "react-icons/hi2";
import { useSurface } from "@/capabilities";
import { Badge, Button, ButtonLink, Input, Panel, cn } from "@/foundation/ui";
import { StationLibrary, type LibraryStation, type StationLibraryScope } from "@/capabilities/stations";
import { errorMessage } from "@/foundation/hooks";
import { plural } from "@/foundation/format";
import { resendInvitation } from "@/domains/assess/roster/api";
import { moveItem } from "@/domains/assess/support";
import type { PickedStation } from "@/domains/assess/CircuitBuilder";
import { displayName } from "@/domains/assess/roster/support";
import { expandToUsers, groupNotice } from "@/domains/assess/support";
import { FieldSelect } from "@/domains/assess/SittingFields";
import {
  CONSULTATION_BOUNDS,
  endsAbout,
  freeBreakPositions,
  type DraftBreak,
  type PickerSet,
  type ScheduleDraft,
  type TraineeRow,
} from "@/domains/assess/scheduleSitting";
import { BREAK_MINUTES_BOUNDS, READING_MINUTES_BOUNDS } from "@/domains/assess/timing";

/**
 * The step bodies of "Schedule a sitting".
 *
 * They are plain controlled components over one value each, so the circuit
 * builder can mount the same station list and the wizard stays one screen of
 * state, not six.
 */

const iconButton =
  "rounded-control p-1.5 text-ink-subtle hover:bg-canvas hover:text-ink disabled:opacity-30 disabled:hover:bg-transparent";

/** One station in the order: drag the handle, or use the arrows and Remove for keyboard and touch. */
function StationRow({
  station,
  index,
  last,
  setStations,
}: {
  station: PickedStation;
  index: number;
  last: boolean;
  setStations: (update: (current: PickedStation[]) => PickedStation[]) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: station.version_id,
  });
  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "flex items-center gap-2 rounded-control border border-border bg-surface px-3 py-1.5 text-sm text-ink",
        isDragging && "relative z-10 shadow-md",
      )}
    >
      <button
        type="button"
        className={cn(iconButton, "cursor-grab touch-none")}
        aria-label={`Drag ${station.title} to reorder`}
        {...attributes}
        {...listeners}
      >
        <HiOutlineBars3 className="h-4 w-4" aria-hidden />
      </button>
      <span className="w-6 text-ink-muted">{index + 1}.</span>
      <span className="min-w-0 flex-1 truncate">{station.title}</span>
      <button
        type="button"
        className={iconButton}
        aria-label={`Move ${station.title} up`}
        disabled={index === 0}
        onClick={() => setStations((current) => moveItem(current, index, -1))}
      >
        <HiOutlineArrowUp className="h-4 w-4" aria-hidden />
      </button>
      <button
        type="button"
        className={iconButton}
        aria-label={`Move ${station.title} down`}
        disabled={last}
        onClick={() => setStations((current) => moveItem(current, index, 1))}
      >
        <HiOutlineArrowDown className="h-4 w-4" aria-hidden />
      </button>
      <button
        type="button"
        className={iconButton}
        aria-label={`Remove ${station.title}`}
        onClick={() => setStations((current) => current.filter((item) => item.version_id !== station.version_id))}
      >
        <HiOutlineTrash className="h-4 w-4" aria-hidden />
      </button>
    </li>
  );
}

/** The ordered stations of a circuit, with the library to add from. */
export function StationOrder({
  stations,
  setStations,
  scope,
  examName,
  heading,
}: {
  stations: PickedStation[];
  setStations: (update: (current: PickedStation[]) => PickedStation[]) => void;
  scope: StationLibraryScope;
  examName: string;
  heading?: string;
}) {
  const { hrefFor } = useSurface();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  return (
    <div className="flex flex-col gap-4">
      {heading ? <p className="text-sm text-ink-muted">{heading}</p> : null}
      {stations.length > 0 && (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={(event: DragEndEvent) => {
            const { active, over } = event;
            if (!over || active.id === over.id) return;
            setStations((current) => {
              const from = current.findIndex((item) => item.version_id === active.id);
              const to = current.findIndex((item) => item.version_id === over.id);
              return from < 0 || to < 0 ? current : arrayMove(current, from, to);
            });
          }}
        >
          <SortableContext items={stations.map((station) => station.version_id)} strategy={verticalListSortingStrategy}>
            <ol className="flex flex-col gap-1.5">
              {stations.map((station, index) => (
                <StationRow
                  key={station.version_id}
                  station={station}
                  index={index}
                  last={index === stations.length - 1}
                  setStations={setStations}
                />
              ))}
            </ol>
          </SortableContext>
        </DndContext>
      )}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-ink">Find a station for {examName}</p>
        <Link
          href={hrefFor("/authoring/stations/new")}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-accent underline"
        >
          Write a new station
        </Link>
      </div>
      <StationLibrary
        scope={scope}
        onPick={(station: LibraryStation) =>
          setStations((current) =>
            current.some((item) => item.version_id === station.version_id)
              ? current
              : [...current, { version_id: station.version_id, title: station.title }],
          )
        }
        pickLabel="Add"
        selectedVersionIds={new Set(stations.map((station) => station.version_id))}
      />
    </div>
  );
}

type PeopleTab = "people" | "groups" | "years";

/** Who sits it: people one by one, or a whole group or year group. */
export function CandidatePicker({
  orgSlug,
  trainees,
  picked,
  setPicked,
  groups,
  yearGroups,
  single,
  words,
}: {
  orgSlug: string;
  trainees: TraineeRow[];
  picked: string[];
  setPicked: (update: (current: string[]) => string[]) => void;
  groups: PickerSet[];
  yearGroups: PickerSet[];
  /** Formal exams make a circuit per person, so the order picked is the order made. */
  single?: boolean;
  words: { trainee: string; trainees: string };
}) {
  const [tab, setTab] = useState<PeopleTab>("people");
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [resent, setResent] = useState<Record<string, string>>({});
  const chosen = new Set(picked);

  const addSet = async (set: PickerSet) => {
    try {
      const result = expandToUsers(await set.loadMemberIds(), trainees);
      setPicked((current) => [...current, ...result.userIds.filter((id) => !current.includes(id))]);
      setNotice(groupNotice(result));
    } catch {
      setNotice(`Could not load ${set.label}. Try again.`);
    }
  };
  const resend = async (trainee: TraineeRow) => {
    try {
      await resendInvitation(orgSlug, trainee.id);
      setResent((current) => ({ ...current, [trainee.id]: "Invitation sent." }));
    } catch (cause) {
      setResent((current) => ({ ...current, [trainee.id]: errorMessage(cause) }));
    }
  };
  const toggle = (userId: string) =>
    setPicked((current) => (current.includes(userId) ? current.filter((id) => id !== userId) : [...current, userId]));

  const needle = search.trim().toLowerCase();
  const visible = trainees.filter((trainee) =>
    `${trainee.first_name ?? ""} ${trainee.last_name ?? ""} ${trainee.email}`.toLowerCase().includes(needle),
  );
  const tabs: { key: PeopleTab; label: string }[] = [
    { key: "people", label: "People" },
    { key: "groups", label: "Groups" },
    { key: "years", label: "Year groups" },
  ];
  const sets = tab === "groups" ? groups : yearGroups;
  const addFromSelect = (list: PickerSet[], id: string) => {
    const set = list.find((item) => item.id === id);
    if (set) void addSet(set);
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-ink-muted">
        {picked.length} of {trainees.filter((trainee) => trainee.user_id !== null).length} selected.
        {single ? " A formal exam circuit is one candidate's sitting: they go through every station." : ""}
      </p>
      {groups.length > 0 || yearGroups.length > 0 ? (
        <div className="flex flex-wrap gap-3">
          {groups.length > 0 ? (
            <FieldSelect
              label="Add a group"
              value=""
              onChange={(value) => addFromSelect(groups, value)}
              options={[{ value: "", label: "Add a group…" }, ...groups.map((set) => ({ value: set.id, label: set.label }))]}
            />
          ) : null}
          {yearGroups.length > 0 ? (
            <FieldSelect
              label="Add a year group"
              value=""
              onChange={(value) => addFromSelect(yearGroups, value)}
              options={[
                { value: "", label: "Add a year group…" },
                ...yearGroups.map((set) => ({ value: set.id, label: set.label })),
              ]}
            />
          ) : null}
        </div>
      ) : null}
      <div role="tablist" aria-label="Pick from" className="flex gap-2">
        {tabs.map((item) => (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={tab === item.key}
            onClick={() => setTab(item.key)}
            className={cn(
              "rounded-full border px-3 py-1 text-sm",
              tab === item.key
                ? "border-b2b-headline bg-b2b-headline text-ink-inverse"
                : "border-b2b-border text-b2b-mid hover:text-b2b-headline",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
      {notice ? (
        <p role="status" className="text-sm text-ink-muted">
          {notice}
        </p>
      ) : null}
      {tab === "people" ? (
        <>
          <div className="max-w-sm">
            <Input
              label="Find a candidate"
              placeholder="Name or email"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          {trainees.length === 0 ? (
            <p className="text-sm text-ink-muted">Add {words.trainees} to your organisation first.</p>
          ) : (
            <ul className="flex flex-col divide-y divide-border rounded-control border border-border">
              {visible.map((trainee) => {
                const userId = trainee.user_id;
                return (
                  <li key={trainee.id} className="flex flex-wrap items-center gap-3 px-3 py-2 text-sm">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-ink">{displayName(trainee)}</p>
                      <p className="truncate text-ink-muted">{trainee.email}</p>
                      {userId === null ? (
                        <p className="text-osce-meta text-ink-muted">
                          Invitation not accepted yet. They can be picked once they accept.
                        </p>
                      ) : null}
                      {resent[trainee.id] ? (
                        <p role="status" className="text-osce-meta text-ink-muted">
                          {resent[trainee.id]}
                        </p>
                      ) : null}
                    </div>
                    {userId === null ? (
                      <>
                        <Badge>Not joined yet</Badge>
                        <Button themeType="b2b" variant="secondary" onClick={() => void resend(trainee)}>
                          Resend invitation
                        </Button>
                      </>
                    ) : (
                      <>
                        <Badge>Signed in</Badge>
                        <Button
                          themeType="b2b"
                          variant={chosen.has(userId) ? "commit" : "secondary"}
                          aria-pressed={chosen.has(userId)}
                          onClick={() => toggle(userId)}
                        >
                          {chosen.has(userId) ? "Picked" : single ? "Pick" : "Add"}
                        </Button>
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </>
      ) : sets.length === 0 ? (
        <p className="text-sm text-ink-muted">
          {tab === "groups" ? "No groups yet." : "No year groups yet."}
        </p>
      ) : (
        <ul className="flex flex-col divide-y divide-border rounded-control border border-border">
          {sets.map((set) => (
            <li key={set.id} className="flex items-center gap-3 px-3 py-2 text-sm">
              <span className="min-w-0 flex-1 truncate">
                <span className="block truncate font-medium text-ink">
                  {tab === "groups" ? "Group" : "Year group"}: {set.label}
                </span>
                {set.count !== undefined ? (
                  <span className="block text-ink-muted">{plural(set.count, words.trainee, words.trainees)}</span>
                ) : null}
              </span>
              <Button themeType="b2b" variant="secondary" onClick={() => void addSet(set)}>
                Add everyone
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const numberOf = (value: string) => (value === "" ? Number.NaN : Number(value));

type Patch = (change: Partial<ScheduleDraft>) => void;

/** Reading time and the consultation: the two lengths every station shares. */
export function DurationInputs({ draft, patch }: { draft: ScheduleDraft; patch: Patch }) {
  return (
    <>
      <Input
        label="Reading time (minutes)"
        type="number"
        min={READING_MINUTES_BOUNDS.min}
        max={READING_MINUTES_BOUNDS.max}
        value={Number.isNaN(draft.readingMinutes) ? "" : draft.readingMinutes}
        hint={`${READING_MINUTES_BOUNDS.min} to ${READING_MINUTES_BOUNDS.max} minutes.`}
        onChange={(event) => patch({ readingMinutes: numberOf(event.target.value) })}
      />
      <Input
        label="Consultation (minutes)"
        type="number"
        min={CONSULTATION_BOUNDS.min}
        max={CONSULTATION_BOUNDS.max}
        value={Number.isNaN(draft.consultationMinutes) ? "" : draft.consultationMinutes}
        hint={`${CONSULTATION_BOUNDS.min} to ${CONSULTATION_BOUNDS.max} minutes.`}
        onChange={(event) => patch({ consultationMinutes: numberOf(event.target.value) })}
      />
    </>
  );
}

/** What a new break lasts before it is changed. */
export function DefaultBreakInput({ draft, patch }: { draft: ScheduleDraft; patch: Patch }) {
  return (
    <>
      <Input
        label="Default break length (minutes)"
        type="number"
        min={BREAK_MINUTES_BOUNDS.min}
        max={BREAK_MINUTES_BOUNDS.max}
        value={Number.isNaN(draft.breakMinutes) ? "" : draft.breakMinutes}
        onChange={(event) => patch({ breakMinutes: numberOf(event.target.value) })}
      />
      <p className="text-sm text-ink-muted">
        A break goes between two stations, never after the last one. Everyone on the circuit pauses during it.
      </p>
    </>
  );
}

/** The breaks between stations: change each one's length, remove it, or add one into a chosen gap. */
export function BreakEditor({ draft, patch }: { draft: ScheduleDraft; patch: Patch }) {
  const free = freeBreakPositions(draft);
  const [gap, setGap] = useState<number | null>(null);
  // The chosen gap may have gone (a station came off, or it was just used): fall back to the first free one.
  const chosen = gap !== null && free.includes(gap) ? gap : (free[0] ?? null);
  const setBreak = (index: number, change: Partial<DraftBreak>) =>
    patch({ breaks: draft.breaks.map((item, at) => (at === index ? { ...item, ...change } : item)) });
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-medium text-ink">Breaks</p>
      {draft.breaks.map((item, index) => (
        <div key={item.after} className="flex items-end gap-2">
          <p className="w-32 pb-2 text-sm text-ink">After station {item.after}</p>
          <Input
            label="Minutes"
            type="number"
            min={BREAK_MINUTES_BOUNDS.min}
            max={BREAK_MINUTES_BOUNDS.max}
            value={Number.isNaN(item.minutes) ? "" : item.minutes}
            onChange={(event) => setBreak(index, { minutes: numberOf(event.target.value) })}
          />
          <Button
            themeType="b2b"
            variant="secondary"
            onClick={() => patch({ breaks: draft.breaks.filter((_, at) => at !== index) })}
          >
            Remove
          </Button>
        </div>
      ))}
      <div className="flex flex-wrap items-end gap-2">
        {free.length > 0 ? (
          <FieldSelect
            label="Add a break after"
            value={String(chosen ?? "")}
            onChange={(value) => setGap(Number(value))}
            options={free.map((position) => ({ value: String(position), label: `Station ${position}` }))}
          />
        ) : null}
        <Button
          themeType="b2b"
          variant="secondary"
          disabled={chosen === null}
          onClick={() =>
            chosen !== null &&
            patch({
              breaks: [...draft.breaks, { after: chosen, minutes: draft.breakMinutes }].sort((a, b) => a.after - b.after),
            })
          }
        >
          Add a break
        </Button>
      </div>
      <p className="text-sm text-ink-muted">
        Each break is {BREAK_MINUTES_BOUNDS.min} to {BREAK_MINUTES_BOUNDS.max} minutes.
      </p>
    </div>
  );
}

/** The wizard's timing step: the lengths, a start time and, for a formal exam, the breaks. */
export function TimingStep({ draft, patch }: { draft: ScheduleDraft; patch: Patch }) {
  const ends = endsAbout(draft);
  return (
    <div className="flex max-w-lg flex-col gap-4">
      <p className="text-sm text-ink-muted">Taken from the exam. Change them for this sitting only.</p>
      <DurationInputs draft={draft} patch={patch} />
      <Input
        label="Start time"
        type="time"
        value={draft.startTime}
        onChange={(event) => patch({ startTime: event.target.value })}
      />
      {draft.mode === "exam" ? <BreakEditor draft={draft} patch={patch} /> : null}
      {ends ? <p className="text-sm text-ink-muted">Ends about {ends} for each candidate.</p> : null}
    </div>
  );
}

/** The one supervisor of a circuit, and the way to invite staff when there is nobody to pick. */
export function SupervisorSelect({
  draft,
  patch,
  leads,
  inviteHref,
}: {
  draft: ScheduleDraft;
  patch: Patch;
  leads: { value: string; label: string }[];
  inviteHref: string;
}) {
  return (
    <>
      <FieldSelect
        label="Supervisor"
        value={draft.supervisorId}
        onChange={(value) => patch({ supervisorId: value })}
        options={[{ value: "", label: "Unassigned" }, ...leads]}
      />
      <p className="text-sm text-ink-muted">
        No supervisors yet?{" "}
        <ButtonLink href={inviteHref} themeType="b2b" variant="ghost">
          Invite staff
        </ButtonLink>
      </p>
    </>
  );
}

/** Who supervises a sitting: one person for all, or one per candidate on a formal exam. */
export function SupervisorStep({
  draft,
  patch,
  leads,
  candidateNames,
  inviteHref,
}: {
  draft: ScheduleDraft;
  patch: Patch;
  leads: { value: string; label: string }[];
  candidateNames: Record<string, string>;
  inviteHref: string;
}) {
  const options = [{ value: "", label: "Unassigned" }, ...leads];
  const canSplit = draft.mode === "exam" && draft.candidateIds.length > 1;
  return (
    <div className="flex max-w-lg flex-col gap-4">
      <p className="text-sm text-ink-muted">
        The supervisor reviews and signs off the circuit afterwards. Any staff member can run the console on the day.
      </p>
      {canSplit ? (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {(
            [
              [false, "One supervisor", "The same person for every circuit"],
              [true, "One each", "A supervisor for each candidate"],
            ] as const
          ).map(([each, title, body]) => (
            <button
              key={title}
              type="button"
              aria-pressed={draft.perCandidate === each}
              onClick={() => patch({ perCandidate: each })}
              className={cn(
                "flex flex-col items-start gap-0.5 rounded-control border px-4 py-3 text-left",
                draft.perCandidate === each ? "border-b2b-headline bg-canvas" : "border-b2b-border bg-b2b-surface hover:bg-canvas",
              )}
            >
              <span className="text-osce-body font-medium text-b2b-headline">{title}</span>
              <span className="text-osce-meta text-b2b-mid">{body}</span>
            </button>
          ))}
        </div>
      ) : null}
      {canSplit && draft.perCandidate ? (
        draft.candidateIds.map((id) => (
          <FieldSelect
            key={id}
            label={candidateNames[id] ?? id}
            value={draft.supervisorByCandidate[id] ?? ""}
            onChange={(value) => patch({ supervisorByCandidate: { ...draft.supervisorByCandidate, [id]: value } })}
            options={options}
          />
        ))
      ) : (
        <SupervisorSelect draft={draft} patch={patch} leads={leads} inviteHref={inviteHref} />
      )}
    </div>
  );
}

/** One labelled row of the review summary. */
export function SummaryRows({ rows }: { rows: [string, string][] }) {
  return (
    <Panel title="Summary">
      <dl className="flex flex-col divide-y divide-border text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4 py-2">
            <dt className="text-ink-muted">{label}</dt>
            <dd className="text-right font-medium text-ink">{value}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  );
}
