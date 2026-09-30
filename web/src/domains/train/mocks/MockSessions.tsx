"use client";

import { memo } from "react";
import Link from "next/link";
import { HiArrowRight } from "react-icons/hi";
import {
  HiOutlineChatBubbleLeftRight,
  HiOutlineClock,
  HiOutlineCreditCard,
  HiOutlineLockClosed,
} from "react-icons/hi2";
import { B2CEmptyState, ButtonLink, ModalHelper, cn, productTokens } from "@/foundation/ui";
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
    <div className="space-y-4">
      {groups.currentSubscription.length > 0 ? (
        <SessionGroup
          title={`Current subscription (${groups.currentSubscription.length})`}
          icon={<HiOutlineCreditCard className="h-4 w-4 text-osce-accent" />}
          defaultOpen
        >
          <ModalHelper className="mb-3 mt-0">
            Active sessions from your current subscription period
          </ModalHelper>
          {grid(groups.currentSubscription)}
        </SessionGroup>
      ) : null}

      {groups.inactiveSubscriptions.length > 0 ? (
        <SessionGroup
          title={`Past subscription (${groups.inactiveSubscriptions.length})`}
          icon={<HiOutlineClock className="h-4 w-4 text-osce-accent" />}
        >
          <ModalHelper className="mb-3 mt-0">
            Sessions from previous subscription periods
          </ModalHelper>
          {grid(groups.inactiveSubscriptions)}
        </SessionGroup>
      ) : null}
    </div>
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
    <div
      className={cn(
        "relative group h-56 p-5 transition-colors duration-300 sm:p-6",
        productTokens.b2cCard,
        "mt-0 hover:bg-b2c-secondary/60",
        set.locked && "border-2",
      )}
    >
      {state === "locked" && (
        <div className="absolute top-2 left-2">
          <span
            className="inline-flex items-center rounded-full border border-b2c-border bg-b2c-secondary px-2.5 py-0.5 text-osce-caption font-medium text-osce-ink-900"
            title="From a past subscription. You can review it, but not reattempt it."
          >
            <HiOutlineLockClosed className="mr-1 h-3 w-3" />
            Review only
          </span>
        </div>
      )}
      {state === "completed" && (
        <div className="absolute top-2 left-2">
          <span className="inline-flex items-center rounded-full bg-osce-success-bg px-2.5 py-0.5 text-osce-caption font-medium text-osce-success-text">
            Completed
          </span>
        </div>
      )}
      {state === "attempted" && (
        <div className="absolute top-2 left-2">
          <span className="inline-flex items-center rounded-full bg-osce-accent-muted px-2.5 py-0.5 text-osce-caption font-medium text-osce-accent-hover">
            Attempted
          </span>
        </div>
      )}

      {set.feedback_ready && (
        <div className="absolute top-2 left-24">
          <span className="inline-flex items-center rounded-full bg-osce-accent-subtle px-2.5 py-0.5 text-osce-caption font-medium text-osce-accent-hover">
            <HiOutlineChatBubbleLeftRight className="mr-1 h-3 w-3" />
            Feedback
          </span>
        </div>
      )}

      <SessionCardActions set={set} onChanged={onChanged} />

      <Link href={hrefFor(`/mocks/${set.id}`)} className="block h-full">
        <div className="mt-4 min-w-0">
          <h2
            className="truncate text-osce-body font-semibold text-osce-ink-900 transition-colors group-hover:text-osce-accent"
            title={set.name}
          >
            {set.name}
          </h2>
          <p
            className={cn(
              "mb-2 max-w-[90%] text-osce-body text-b2c-text-secondary",
              set.locked ? "line-clamp-1" : "line-clamp-3",
            )}
          >
            Practice your consultation skills with these clinical scenarios.
          </p>
          {set.locked && (
            <p className="mb-4 line-clamp-2 text-osce-meta text-b2c-text-muted">
              From a past subscription. Review your feedback and transcripts any time — reattempts
              aren&apos;t available.
            </p>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-b2c-border-light pt-2 lg:mt-12">
          <div className="flex items-center gap-1 md:gap-2">
            <span className="flex items-center whitespace-nowrap text-osce-body text-b2c-text-muted">
              <HiOutlineClock className="mr-1 h-4 w-4" />
              {`${minutes} mins`}
            </span>
            <span className="whitespace-nowrap text-osce-body text-b2c-text-muted">
              {set.total_entries} stations
            </span>
          </div>
          <span className="flex items-center whitespace-nowrap text-osce-body font-medium text-osce-accent transition-transform group-hover:translate-x-1">
            {sessionAction(set)}
            <HiArrowRight className="ml-1 h-4 w-4" />
          </span>
        </div>
      </Link>
    </div>
  );
});
