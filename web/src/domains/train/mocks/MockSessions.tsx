"use client";

import { memo, type ReactNode } from "react";
import Link from "next/link";
import { HiArrowRight } from "react-icons/hi";
import { HiOutlineClock, HiOutlineLockClosed } from "react-icons/hi2";
import { B2CEmptyState, ButtonLink, cn, productTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import type { Exam } from "@/capabilities/stations";
import type { StationSet } from "@/domains/train/api";
import { SessionCardActions } from "@/domains/train/mocks/SessionCardActions";
import { SessionGroup } from "@/domains/train/mocks/SessionGroup";
import { groupSets, sessionAction, sessionMinutes, sessionState } from "@/domains/train/mocks/model";

/**
 * Every session this person has for this exam, newest first: the retiring
 * `MockList`'s groups and cards.
 *
 * Sorting is the backend's order; sets come back newest first. `onChanged` is
 * the list's reload, so what appears after a delete is what the server says.
 */
export function MockSessions({
  sets,
  exams,
  onChanged,
}: {
  sets: StationSet[];
  exams: Exam[];
  onChanged: () => void;
}) {
  const { hrefFor } = useSurface();
  const groups = groupSets(sets);
  const isEmpty =
    groups.currentSubscription.length === 0 && groups.inactiveSubscriptions.length === 0;

  if (isEmpty) {
    return (
      <B2CEmptyState
        className="mt-8"
        title="No sessions yet"
        description="Create your first session to practise with an AI patient. It takes about 12 minutes per station."
        action={
          <ButtonLink href={hrefFor("/mocks")} variant="primary" size="md">
            Create your first session
          </ButtonLink>
        }
      />
    );
  }

  const grid = (items: StationSet[]) => (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {items.map((set) => (
        <SessionCard
          key={set.id}
          set={set}
          exam={exams.find((exam) => exam.code === set.exam_code) ?? null}
          onChanged={onChanged}
        />
      ))}
    </div>
  );

  return (
    <div className="space-y-6">
      {groups.currentSubscription.length > 0 ? (
        <SessionGroup title={`Current subscription · ${groups.currentSubscription.length}`}>
          {grid(groups.currentSubscription)}
        </SessionGroup>
      ) : null}

      {groups.inactiveSubscriptions.length > 0 ? (
        <SessionGroup title={`Past subscription · ${groups.inactiveSubscriptions.length}`}>
          {grid(groups.inactiveSubscriptions)}
        </SessionGroup>
      ) : null}
    </div>
  );
}

/** A 22px pill with a status dot (canvas `train-sessions`). */
function StatusPill({ dot, children }: { dot: string; children: ReactNode }) {
  return (
    <span className="inline-flex h-[22px] items-center gap-1.5 rounded-osce-sm bg-b2c-surface-muted px-2 text-osce-caption font-medium text-osce-ink-700">
      <span className={cn("h-1.5 w-1.5 rounded-full", dot)} aria-hidden />
      {children}
    </span>
  );
}

const SessionCard = memo(function SessionCard({
  set,
  exam,
  onChanged,
}: {
  set: StationSet;
  exam: Exam | null;
  onChanged: () => void;
}) {
  const { hrefFor } = useSurface();
  const state = sessionState(set);
  const minutes = sessionMinutes(
    set.total_entries,
    exam
      ? {
          readingSeconds: exam.default_reading_seconds,
          simulationSeconds: exam.default_simulation_seconds,
        }
      : null,
  );

  return (
    <div className={cn("group relative flex min-h-[200px] flex-col gap-3 p-5 transition-colors hover:bg-osce-surface-inset", productTokens.b2cCard)}>
      <div className="flex items-center justify-between gap-2">
        <span className="flex flex-wrap gap-1.5">
          {state === "locked" ? (
            <span
              className="inline-flex h-[22px] items-center gap-1.5 rounded-osce-sm bg-b2c-surface-muted px-2 text-osce-caption font-medium text-osce-ink-700"
              title="From a past subscription. You can review it, but not reattempt it."
            >
              <HiOutlineLockClosed className="h-3 w-3" aria-hidden />
              Review only
            </span>
          ) : state === "completed" ? (
            <StatusPill dot="bg-osce-success-icon">Completed</StatusPill>
          ) : state === "attempted" ? (
            <StatusPill dot="bg-osce-accent">Attempted</StatusPill>
          ) : null}
          {set.feedback_ready ? <StatusPill dot="bg-osce-accent">Feedback</StatusPill> : null}
        </span>
        <SessionCardActions set={set} onChanged={onChanged} />
      </div>

      <Link href={hrefFor(`/mocks/${set.id}`)} className="flex flex-1 flex-col gap-3 after:absolute after:inset-0 after:content-['']">
        <h3 className={cn("truncate", productTokens.b2cSectionTitle)} title={set.name}>
          {set.name}
        </h3>
        <p className="line-clamp-3 flex-1 text-b2c-text-muted">
          {set.locked
            ? "From a past subscription. Review your feedback and transcripts any time."
            : "Practise your consultation skills with these clinical scenarios."}
        </p>
        <div className="flex items-center gap-3.5 border-t border-b2c-border-light pt-3 text-osce-meta text-b2c-text-muted">
          <span className="flex items-center gap-1 whitespace-nowrap">
            <HiOutlineClock className="h-3.5 w-3.5" aria-hidden />
            {minutes} mins
          </span>
          <span className="whitespace-nowrap">
            {set.total_entries} {set.total_entries === 1 ? "station" : "stations"}
          </span>
          <span className="ml-auto flex items-center gap-1 whitespace-nowrap font-medium text-osce-accent">
            {sessionAction(set)}
            <HiArrowRight className="h-3.5 w-3.5" aria-hidden />
          </span>
        </div>
      </Link>
    </div>
  );
});
