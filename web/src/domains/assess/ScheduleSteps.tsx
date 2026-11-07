"use client";

import { boardBtn } from "@/foundation/ui/boardKit";
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
import { useSurface } from "@/capabilities";
import { b2bTokens as t, cn, Modal } from "@/foundation/ui";
import {
  StationLibrary,
  type LibraryStation,
  type StationLibraryScope,
} from "@/capabilities/stations";
import { errorMessage } from "@/foundation/hooks";
import { plural } from "@/foundation/format";
import { resendInvitation } from "@/domains/assess/roster/api";
import { moveItem } from "@/domains/assess/support";
import type { PickedStation } from "@/domains/assess/CircuitBuilder";
import { displayName } from "@/domains/assess/roster/support";
import { expandToUsers, groupNotice } from "@/domains/assess/support";
import {
  Chip,
  Field,
  FieldSelect,
  OptionCards,
  fieldInput,
  flushCard,
  flushRow,
  smallButton,
  Note,
} from "@/domains/assess/SittingFields";
import {
  CONSULTATION_BOUNDS,
  SUPERVISOR_OPTIONS,
  candidateStanding,
  endsAbout,
  freeBreakPositions,
  type DraftBreak,
  type PickerSet,
  type ScheduleDraft,
  type TraineeRow,
  STAGGER_BOUNDS,
} from "@/domains/assess/scheduleSitting";
import {
  BREAK_MINUTES_BOUNDS,
  READING_MINUTES_BOUNDS,
} from "@/domains/assess/timing";
import { RotationBuilder } from "@/domains/assess/RotationBuilder";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * The step bodies of "Schedule a sitting" (docs/institution-overhaul/boards/ScheduleSitting.dc.html).
 *
 * They are plain controlled components over one value each, so the circuit
 * builder can mount the same station list and the wizard stays one screen of
 * state, not six.
 */

/** A text link in the board's blue; the globals never remap a link's colour. */
export const linkClass = "text-osce-accent hover:text-osce-accent-hover";

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
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: station.version_id,
  });
  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        flushRow,
        "bg-osce-surface",
        isDragging && "relative z-10 shadow-md",
      )}
    >
      <button
        type="button"
        className="w-4 cursor-grab touch-none text-base text-ink-subtle"
        aria-label={`Drag ${station.title} to reorder`}
        {...attributes}
        {...listeners}
      >
        <span aria-hidden="true">⋮⋮</span>
      </button>
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-osce-navActive text-assess-chip">
        {index + 1}
      </span>
      <span className="min-w-0 flex-[1_1_220px] font-medium">
        {station.title}
      </span>
      <button
        type="button"
        className={smallButton}
        aria-label={`Move ${station.title} up`}
        disabled={index === 0}
        onClick={() => setStations((current) => moveItem(current, index, -1))}
      >
        ↑
      </button>
      <button
        type="button"
        className={smallButton}
        aria-label={`Move ${station.title} down`}
        disabled={last}
        onClick={() => setStations((current) => moveItem(current, index, 1))}
      >
        ↓
      </button>
      <button
        type="button"
        className={smallButton}
        aria-label={`Remove ${station.title}`}
        onClick={() =>
          setStations((current) =>
            current.filter((item) => item.version_id !== station.version_id),
          )
        }
      >
        Remove
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
  note,
}: {
  stations: PickedStation[];
  setStations: (update: (current: PickedStation[]) => PickedStation[]) => void;
  scope: StationLibraryScope;
  examName: string;
  heading?: string;
  /** How many are picked, as a tinted line above the list. */
  note?: string;
}) {
  const { hrefFor } = useSurface();
  const [adding, setAdding] = useState(false);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );
  return (
    <div className="flex flex-col gap-6">
      {heading ? <p className="text-sm text-ink-muted">{heading}</p> : null}
      {note ? <Note tone="info">{note}</Note> : null}
      {stations.length > 0 ? (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={(event: DragEndEvent) => {
            const { active, over } = event;
            if (!over || active.id === over.id) return;
            setStations((current) => {
              const from = current.findIndex(
                (item) => item.version_id === active.id,
              );
              const to = current.findIndex(
                (item) => item.version_id === over.id,
              );
              return from < 0 || to < 0
                ? current
                : arrayMove(current, from, to);
            });
          }}
        >
          <SortableContext
            items={stations.map((station) => station.version_id)}
            strategy={verticalListSortingStrategy}
          >
            <ol className={flushCard}>
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
      ) : (
        <p className={t.assessMeta}>
          No stations picked yet. Add some from {examName}.
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className={boardBtn()}
          onClick={() => setAdding(true)}
        >
          Add from this exam
        </button>
        <Link
          href={hrefFor("/authoring/stations/new")}
          target="_blank"
          rel="noreferrer"
          className={boardBtn()}
        >
          Write a new station
        </Link>
      </div>
      {adding ? (
        <Modal
          title={`Add from ${examName}`}
          onClose={() => setAdding(false)}
          width={{ mobile: "100%", desktop: "48rem" }}
        >
          <div className="flex flex-col gap-6">
            <h2 className={t.assessTitle}>Find a station for {examName}</h2>
            <StationLibrary
              scope={scope}
              onPick={(station: LibraryStation) =>
                setStations((current) =>
                  current.some((item) => item.version_id === station.version_id)
                    ? current
                    : [
                        ...current,
                        {
                          version_id: station.version_id,
                          title: station.title,
                        },
                      ],
                )
              }
              pickLabel="Add"
              selectedVersionIds={
                new Set(stations.map((station) => station.version_id))
              }
            />
            <div className="flex justify-end">
              <button
                type="button"
                className={boardBtn("primary")}
                onClick={() => setAdding(false)}
              >
                Done
              </button>
            </div>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

type PeopleTab = "people" | "groups" | "years";

/** The board's `.tabs`: a pill strip, the chosen tab raised on white. */
function Segments<T extends string>({
  label,
  tabs,
  value,
  onChange,
}: {
  label: string;
  tabs: { key: T; label: string }[];
  value: T;
  onChange: (key: T) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className="inline-flex flex-wrap gap-0.5 rounded-osce-md bg-osce-navActive p-[3px]"
    >
      {tabs.map((item) => (
        <button
          key={item.key}
          type="button"
          role="tab"
          aria-selected={value === item.key}
          onClick={() => onChange(item.key)}
          className={cn(
            "inline-flex min-h-9 items-center rounded-osce-sm px-3.5 text-assess-label",
            value === item.key
              ? "bg-osce-surface font-medium text-ink"
              : "text-osce-ink-700",
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

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
  showCount = true,
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
  /** The wizard says the count in a note below instead. */
  showCount?: boolean;
}) {
  const w = useAssessWords();
  const [tab, setTab] = useState<PeopleTab>("people");
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [resent, setResent] = useState<Record<string, string>>({});
  const chosen = new Set(picked);

  const addSet = async (set: PickerSet) => {
    try {
      const result = expandToUsers(await set.loadMemberIds(), trainees);
      setPicked((current) => [
        ...current,
        ...result.userIds.filter((id) => !current.includes(id)),
      ]);
      setNotice(groupNotice(result));
    } catch {
      setNotice(`Could not load ${set.label}. Try again.`);
    }
  };
  const resend = async (trainee: TraineeRow) => {
    try {
      await resendInvitation(orgSlug, trainee.id);
      setResent((current) => ({
        ...current,
        [trainee.id]: "Invitation sent.",
      }));
    } catch (cause) {
      setResent((current) => ({
        ...current,
        [trainee.id]: errorMessage(cause),
      }));
    }
  };
  const toggle = (userId: string) =>
    setPicked((current) =>
      current.includes(userId)
        ? current.filter((id) => id !== userId)
        : [...current, userId],
    );

  const needle = search.trim().toLowerCase();
  const visible = trainees.filter((trainee) =>
    `${trainee.first_name ?? ""} ${trainee.last_name ?? ""} ${trainee.email}`
      .toLowerCase()
      .includes(needle),
  );
  const tabs: { key: PeopleTab; label: string }[] = [
    { key: "people", label: "People" },
    { key: "groups", label: "Groups" },
    { key: "years", label: w.YearGroups },
  ];
  const sets = tab === "groups" ? groups : yearGroups;

  return (
    <div className="flex flex-col gap-6">
      {showCount ? (
        <p className={t.assessMeta}>
          {picked.length} of{" "}
          {trainees.filter((trainee) => trainee.user_id !== null).length}{" "}
          selected.
          {single
            ? ` A formal exam ${w.circuit} is one candidate's ${w.sitting}: they go through every station.`
            : ""}
        </p>
      ) : null}
      <Segments label="Pick from" tabs={tabs} value={tab} onChange={setTab} />
      {notice ? (
        <p role="status" className={t.assessMeta}>
          {notice}
        </p>
      ) : null}
      {tab === "people" ? (
        <>
          <input
            className={fieldInput}
            placeholder="Search by name or email"
            aria-label={`Search ${w.trainees}`}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          {trainees.length === 0 ? (
            <p className={t.assessMeta}>
              Add {words.trainees} to your organisation first.
            </p>
          ) : (
            <ul className={flushCard}>
              {visible.map((trainee) => {
                const userId = trainee.user_id;
                const standing = candidateStanding(trainee);
                const on = userId !== null && chosen.has(userId);
                return (
                  <li key={trainee.id} className={flushRow}>
                    {userId === null ? (
                      <span
                        aria-hidden="true"
                        className="box-border h-[18px] w-[18px] shrink-0 rounded-board-xs border border-border-strong"
                      />
                    ) : null}
                    {userId !== null ? (
                      <label className="flex min-w-0 flex-[1_1_220px] cursor-pointer items-center gap-3.5">
                        <input
                          type="checkbox"
                          className="peer sr-only"
                          checked={on}
                          onChange={() => toggle(userId)}
                        />
                        <span
                          aria-hidden="true"
                          className={cn(
                            "box-border flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-board-xs border text-[12px] leading-none text-white peer-focus-visible:ring-2",
                            on
                              ? "border-osce-accent bg-osce-accent"
                              : "border-border-strong bg-osce-surface",
                          )}
                        >
                          {on ? "✓" : null}
                        </span>
                        <span className="min-w-0">
                          <span className="font-medium">
                            {displayName(trainee)}
                          </span>
                          <span className={cn(t.assessMeta, "block")}>
                            {trainee.email}
                          </span>
                        </span>
                      </label>
                    ) : (
                      <span className="min-w-0 flex-[1_1_220px]">
                        <span className="font-medium">
                          {displayName(trainee)}
                        </span>
                        <span className={cn(t.assessMeta, "block")}>
                          {"Can't be scheduled until they accept."}
                        </span>
                        {resent[trainee.id] ? (
                          <span
                            role="status"
                            className={cn(t.assessMeta, "block")}
                          >
                            {resent[trainee.id]}
                          </span>
                        ) : null}
                      </span>
                    )}
                    {standing === "signed_in" ? (
                      <Chip tone="ok">Signed in</Chip>
                    ) : (
                      <>
                        <Chip tone="warn">
                          {standing === "invited" ? "Invited, not accepted" : "Not joined yet"}
                        </Chip>
                        <button
                          type="button"
                          className={smallButton}
                          onClick={() => void resend(trainee)}
                        >
                          Resend invitation
                        </button>
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </>
      ) : sets.length === 0 ? (
        <p className={t.assessMeta}>
          {tab === "groups" ? "No groups yet." : `No ${w.yearGroups} yet.`}
        </p>
      ) : (
        <ul className={flushCard}>
          {sets.map((set) => (
            <li key={set.id} className={flushRow}>
              <span className="min-w-0 flex-[1_1_220px]">
                <span className="font-medium">
                  {tab === "groups" ? "Group" : w.YearGroup}: {set.label}
                </span>
                {set.count !== undefined ? (
                  <span className={cn(t.assessMeta, "block")}>
                    {plural(set.count, words.trainee, words.trainees)}
                  </span>
                ) : null}
              </span>
              <Chip tone="info">
                {tab === "groups" ? "Group" : w.YearGroup}
              </Chip>
              <button
                type="button"
                className={smallButton}
                onClick={() => void addSet(set)}
              >
                Add everyone
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const numberOf = (value: string) => (value === "" ? Number.NaN : Number(value));

type Patch = (change: Partial<ScheduleDraft>) => void;

/** One whole-minutes field: blank while the draft holds NaN, bounded by the same limits the api checks. */
function MinutesInput({
  id,
  label,
  describedBy,
  className,
  bounds,
  value,
  onValue,
}: {
  id?: string;
  label?: string;
  describedBy: string;
  className?: string;
  bounds: { min: number; max: number };
  value: number;
  onValue: (minutes: number) => void;
}) {
  return (
    <input
      id={id}
      className={cn(fieldInput, className)}
      type="number"
      aria-label={label}
      aria-describedby={describedBy}
      min={bounds.min}
      max={bounds.max}
      value={Number.isNaN(value) ? "" : value}
      onChange={(event) => onValue(numberOf(event.target.value))}
    />
  );
}

/** Reading time and the consultation: the two lengths every station shares. */
export function DurationInputs({
  draft,
  patch,
}: {
  draft: ScheduleDraft;
  patch: Patch;
}) {
  return (
    <>
      <Field
        label="Reading time"
        htmlFor="sitting-reading"
        hint={`${READING_MINUTES_BOUNDS.min} to ${READING_MINUTES_BOUNDS.max} min`}
      >
        <MinutesInput
          id="sitting-reading"
          describedBy="sitting-reading-hint"
          bounds={READING_MINUTES_BOUNDS}
          value={draft.readingMinutes}
          onValue={(readingMinutes) => patch({ readingMinutes })}
        />
      </Field>
      <Field
        label="Consultation"
        htmlFor="sitting-consultation"
        hint={`${CONSULTATION_BOUNDS.min} to ${CONSULTATION_BOUNDS.max} min`}
      >
        <MinutesInput
          id="sitting-consultation"
          describedBy="sitting-consultation-hint"
          bounds={CONSULTATION_BOUNDS}
          value={draft.consultationMinutes}
          onValue={(consultationMinutes) => patch({ consultationMinutes })}
        />
      </Field>
    </>
  );
}

/** What a new break lasts before it is changed. */
export function DefaultBreakInput({
  draft,
  patch,
}: {
  draft: ScheduleDraft;
  patch: Patch;
}) {
  const w = useAssessWords();
  return (
    <Field
      label="Default break length (minutes)"
      htmlFor="sitting-default-break"
      hint={`A break goes between two stations, never after the last one. Everyone on the ${w.circuit} pauses during it.`}
    >
      <MinutesInput
        id="sitting-default-break"
        describedBy="sitting-default-break-hint"
        bounds={BREAK_MINUTES_BOUNDS}
        value={draft.breakMinutes}
        onValue={(breakMinutes) => patch({ breakMinutes })}
      />
    </Field>
  );
}

/** The breaks between stations: change each one's length, remove it, or add one into a chosen gap. */
export function BreakEditor({
  draft,
  patch,
}: {
  draft: ScheduleDraft;
  patch: Patch;
}) {
  const free = freeBreakPositions(draft);
  const [gap, setGap] = useState<number | null>(null);
  // The chosen gap may have gone (a station came off, or it was just used): fall back to the first free one.
  const chosen = gap !== null && free.includes(gap) ? gap : (free[0] ?? null);
  const setBreak = (index: number, change: Partial<DraftBreak>) =>
    patch({
      breaks: draft.breaks.map((item, at) =>
        at === index ? { ...item, ...change } : item,
      ),
    });
  return (
    <div className="flex flex-col gap-2">
      <p className="text-assess-label font-medium">Breaks</p>
      {draft.breaks.length > 0 ? (
        <ul className={cn(flushCard, "rounded-osce-md")}>
          {draft.breaks.map((item, index) => (
            <li key={item.after} className={flushRow}>
              <span className="min-w-0 flex-[1_1_200px]">
                After station {item.after}
              </span>
              <MinutesInput
                className="w-[120px]"
                label={`Break length after station ${item.after}`}
                describedBy="sitting-break-range"
                bounds={BREAK_MINUTES_BOUNDS}
                value={item.minutes}
                onValue={(minutes) => setBreak(index, { minutes })}
              />
              <button
                type="button"
                className={smallButton}
                onClick={() =>
                  patch({
                    breaks: draft.breaks.filter((_, at) => at !== index),
                  })
                }
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className={smallButton}
          disabled={chosen === null}
          onClick={() =>
            chosen !== null &&
            patch({
              breaks: [
                ...draft.breaks,
                { after: chosen, minutes: draft.breakMinutes },
              ].sort((a, b) => a.after - b.after),
            })
          }
        >
          Add a break
        </button>
        {free.length > 1 ? (
          <select
            aria-label="Add a break after"
            className={cn(fieldInput, "min-h-9 w-auto text-assess-meta")}
            value={String(chosen ?? "")}
            onChange={(event) => setGap(Number(event.target.value))}
          >
            {free.map((position) => (
              <option key={position} value={position}>
                After station {position}
              </option>
            ))}
          </select>
        ) : null}
        <span id="sitting-break-range" className={t.assessMeta}>
          Each break is {BREAK_MINUTES_BOUNDS.min} to {BREAK_MINUTES_BOUNDS.max}{" "}
          minutes.
        </span>
      </div>
    </div>
  );
}

/** The wizard's timing step: the lengths, a start time and, for a formal exam, the breaks. */
export function TimingStep({
  draft,
  patch,
}: {
  draft: ScheduleDraft;
  patch: Patch;
}) {
  const w = useAssessWords();
  const ends = endsAbout(draft);
  return (
    <div className={cn(t.assessCard, "p-6", t.assessFormStack)}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <DurationInputs draft={draft} patch={patch} />
        <Field label="Start time" htmlFor="sitting-start">
          <input
            id="sitting-start"
            className={fieldInput}
            type="time"
            value={draft.startTime}
            onChange={(event) => patch({ startTime: event.target.value })}
          />
        </Field>
      </div>
      {draft.mode === "exam" ? (
        <div className="border-t border-osce-border-light pt-7">
          <BreakEditor draft={draft} patch={patch} />
        </div>
      ) : null}
      {w.hiring && draft.mode === "exam" ? (
        <div className="border-t border-osce-border-light pt-7">
          <Field label={`Stagger ${w.circuits} (minutes apart)`} htmlFor="sitting-stagger">
            <input
              id="sitting-stagger"
              className={cn(fieldInput, "w-32")}
              type="number"
              inputMode="numeric"
              min={STAGGER_BOUNDS.min}
              max={STAGGER_BOUNDS.max}
              value={draft.staggerMinutes}
              onChange={(event) =>
                patch({
                  staggerMinutes: Math.min(
                    STAGGER_BOUNDS.max,
                    Math.max(STAGGER_BOUNDS.min, Math.round(Number(event.target.value)) || 0),
                  ),
                })
              }
            />
          </Field>
          <p className={cn(t.assessMeta, "mt-2")}>
            {draft.staggerMinutes > 0
              ? `Each ${w.trainee} starts ${draft.staggerMinutes} minutes after the one before. The first starts at the start time.`
              : `0 starts every ${w.trainee} together at the start time.`}
          </p>
        </div>
      ) : null}
      {ends ? (
        <Note tone="info">Ends about {ends} for each candidate.</Note>
      ) : null}
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
  const w = useAssessWords();
  return (
    <>
      <FieldSelect
        label={w.Supervisor}
        id="sitting-supervisor"
        value={draft.supervisorId}
        onChange={(value) => patch({ supervisorId: value })}
        options={[{ value: "", label: "Unassigned" }, ...leads]}
      />
      <p className={t.assessMeta}>
        {`No ${w.supervisors} yet?`}{" "}
        <Link href={inviteHref} className={linkClass}>
          Invite staff
        </Link>
      </p>
    </>
  );
}

/** Hire: a different assessor for each station; a station left on the default is the lead's. */
function StationAssessors({
  draft,
  patch,
  options,
}: {
  draft: ScheduleDraft;
  patch: Patch;
  options: { value: string; label: string }[];
}) {
  const w = useAssessWords();
  return (
    <div className={cn(t.assessCard, "p-6", t.assessFormStack)}>
      <p className="font-medium">{w.Supervisor} for each station</p>
      <p className={t.assessMeta}>
        A station left on the default is assessed by the {w.circuit}&apos;s own {w.supervisor}. An assessor
        sees and marks only their station.
      </p>
      <ul className={flushCard}>
        {draft.stations.map((station, at) => (
          <li key={station.version_id} className={flushRow}>
            <span className="min-w-0 flex-[1_1_200px] font-medium">{`Station ${at + 1}: ${station.title}`}</span>
            <select
              className={cn(fieldInput, "w-[200px]")}
              aria-label={`${w.Supervisor} for station ${at + 1}`}
              value={draft.stationAssessors[station.version_id] ?? ""}
              onChange={(event) =>
                patch({
                  stationAssessors: { ...draft.stationAssessors, [station.version_id]: event.target.value },
                })
              }
            >
              {options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.value === "" ? "Default" : option.label}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
    </div>
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
  const w = useAssessWords();
  const options = [{ value: "", label: "Unassigned" }, ...leads];
  const canSplit = draft.mode === "exam" && draft.candidateIds.length > 1;
  const each = canSplit && draft.perCandidate;
  return (
    <div className="flex flex-col gap-6">
      {canSplit ? (
        <OptionCards
          label="Who supervises"
          options={SUPERVISOR_OPTIONS.map((option) => ({
            key: option.title,
            title: option.title,
            body: option.body,
            selected: draft.perCandidate === option.each,
            onSelect: () => patch({ perCandidate: option.each }),
          }))}
        />
      ) : null}
      {each && w.hiring ? <RotationBuilder draft={draft} patch={patch} leads={leads} /> : null}
      {w.hiring && draft.mode === "exam" && draft.stations.length > 0 ? (
        <StationAssessors draft={draft} patch={patch} options={options} />
      ) : null}
      {each ? (
        <ul className={flushCard}>
          {draft.candidateIds.map((id) => (
            <li key={id} className={flushRow}>
              <span className="min-w-0 flex-[1_1_200px] font-medium">
                {candidateNames[id] ?? id}
              </span>
              <select
                className={cn(fieldInput, "w-[200px]")}
                aria-label={`${w.Supervisor} for ${candidateNames[id] ?? id}`}
                value={draft.supervisorByCandidate[id] ?? ""}
                onChange={(event) =>
                  patch({
                    supervisorByCandidate: {
                      ...draft.supervisorByCandidate,
                      [id]: event.target.value,
                    },
                  })
                }
              >
                {options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </li>
          ))}
        </ul>
      ) : (
        <div className={cn(t.assessCard, "p-6", t.assessFormStack)}>
          <SupervisorSelect
            draft={draft}
            patch={patch}
            leads={leads}
            inviteHref={inviteHref}
          />
        </div>
      )}
    </div>
  );
}

/** The review's headline sum: big, with what it means under it. */
export function ReviewFormula({
  formula,
  help,
}: {
  formula: string;
  help: string;
}) {
  return (
    <div className={cn(t.assessCard, "flex flex-col items-start gap-1.5 p-6")}>
      <div className="text-[22px] font-semibold">{formula}</div>
      <div className={t.assessMeta}>{help}</div>
    </div>
  );
}

/** One labelled row of the review summary. */
export function SummaryRows({ rows }: { rows: [string, string][] }) {
  return (
    <dl className={cn(t.assessCard, "px-6")}>
      {rows.map(([label, value]) => (
        <div
          key={label}
          className="flex flex-wrap justify-between gap-4 border-t border-osce-border-light py-3 text-assess-label first:border-t-0"
        >
          <dt className={t.assessMeta}>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
