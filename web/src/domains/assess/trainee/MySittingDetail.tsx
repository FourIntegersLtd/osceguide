"use client";

import { HiOutlinePresentationChartLine } from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  Badge,
  ButtonLink,
  EmptyState,
  TextLink,
  b2bTokens,
} from "@/foundation/ui";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { JoinRoom } from "@/domains/assess/trainee/JoinRoom";
import {
  MY_SITTINGS_STREAM,
  readMyResult,
  readMySittings,
  type MySitting,
  type MySittings,
  type MySlot,
} from "@/domains/assess/trainee/api";
import {
  isExam,
  modeLabel,
  orderedSlots,
  progressOf,
  slotStatus,
} from "@/domains/assess/trainee/support";

/**
 * One sitting, as the candidate sitting it sees it.
 *
 * There is no per-sitting read for a candidate and there does not need to be:
 * `/me/sittings` already carries every slot this person owns, and it streams.
 * So this screen is a projection of the same feed the overview renders — one
 * subscription's worth of data, two screens — where the retiring arm had a
 * second endpoint polled every five seconds.
 *
 * A sitting is identified by its circuit here as well as its id, because one
 * sitting can run several circuits and a candidate is rostered onto one of
 * them. Keying on the sitting alone showed somebody another circuit's stations.
 */
export function MySittingDetail({ sittingId }: { sittingId: string }) {
  const initial = useAsync((signal) => readMySittings(signal), []);
  const stream = useEventStream<MySittings>(MY_SITTINGS_STREAM);
  const data = stream.data ?? initial.data;
  const mine = (data?.items ?? []).filter((sitting) => sitting.id === sittingId);

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <AsyncBoundary state={initial} isEmpty={() => mine.length === 0}
        empty={{
          title: "We could not find that sitting",
          description: "You may have been taken off it, or it belongs to another workspace.",
        }}
      >
        {() => (
          <>
            {mine.map((sitting) => (
              <Circuit key={sitting.circuit_id} sitting={sitting} />
            ))}
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}

function Circuit({ sitting }: { sitting: MySitting }) {
  const { hrefFor } = useSurface();
  const slots = orderedSlots(sitting);
  const { completed, total } = progressOf(sitting);
  const exam = isExam(sitting);

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-b2b-border pb-4">
        <div className="min-w-0">
          <p className={b2bTokens.b2bEyebrow}>{modeLabel(sitting)}</p>
          <h1 className={`mt-1 ${b2bTokens.b2bPageTitle}`}>{sitting.name}</h1>
          <p className="mt-1 text-osce-caption text-b2b-mid">
            {sitting.circuit_name}
            {total > 0 ? ` · ${completed} of ${total} stations completed` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {sitting.live ? <Badge tone="success">Live</Badge> : null}
          {sitting.paused ? <Badge tone="warning">Paused</Badge> : null}
          <ButtonLink themeType="b2b" variant="secondary" size="sm" href={hrefFor("/trainee")}>
            All sittings
          </ButtonLink>
        </div>
      </header>

      <Alert tone="info" title={exam ? "Before you start" : "How a practice circuit works"}>
        {exam
          ? "Your station opens on the supervisor's signal. Go straight in — the patient joins when the reading time ends, and the room has to be occupied before then."
          : "Your supervisor opens the room. Only the person on turn speaks with the patient; the circuit's feedback appears once it is published."}
      </Alert>

      {sitting.can_join ? (
        <div className="rounded-lg border border-b2b-border bg-b2b-surface p-4 sm:p-5">
          <h2 className={b2bTokens.b2bSectionTitle}>Your station is open</h2>
          <div className="mt-3">
            <JoinRoom sitting={sitting} />
          </div>
        </div>
      ) : null}

      <div className="space-y-2">
        <h2 className={b2bTokens.b2bEyebrow}>{exam ? "Your stations" : "Your turns"}</h2>
        {slots.length === 0 ? (
          <EmptyState
            title="Nothing assigned yet"
            description="When your organisation adds stations for you on this circuit, they appear here."
          />
        ) : (
          <ul className="flex flex-col gap-2">
            {slots.map((slot) => (
              <li key={slot.id}>
                <Slot slot={slot} exam={exam} />
              </li>
            ))}
          </ul>
        )}
      </div>

      <MyResultLink sittingId={sitting.id} />
    </section>
  );
}

/**
 * One station on the circuit.
 *
 * The record is offered only once there is an attempt to read — the transcript
 * and the marking both hang off it, so a link without one is a page that can
 * only apologise. The retiring screen offered "Station record" on every row,
 * finished or not.
 */
function Slot({ slot, exam }: { slot: MySlot; exam: boolean }) {
  const { hrefFor } = useSurface();
  const status = slotStatus(slot);

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-b2b-border bg-b2b-surface p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <span
          className={`${b2bTokens.b2bIconChipBase} ${b2bTokens.b2bChipHueClasses.violet} ${
            status.done ? "opacity-45" : ""
          }`}
        >
          <HiOutlinePresentationChartLine className="h-5 w-5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p
              className={`text-osce-body font-semibold ${
                status.done ? "text-b2b-mid" : "text-b2b-headline"
              }`}
            >
              {exam ? "Station" : "Turn"} {slot.slot_index + 1}
            </p>
            <Badge tone={status.tone}>{status.label}</Badge>
          </div>
          {slot.station_title ? (
            <p className="mt-0.5 text-osce-meta text-b2b-mid">{slot.station_title}</p>
          ) : null}
          {status.done ? (
            <p className="mt-2 text-osce-meta text-b2b-mid">
              Read this one back below. A finished station cannot be re-entered.
            </p>
          ) : null}
        </div>
      </div>

      {slot.attempt_id ? (
        <ButtonLink
          themeType="b2b"
          variant={status.done ? "commit" : "secondary"}
          size="sm"
          href={hrefFor(`/attempts/${slot.attempt_id}`)}
          className="w-full sm:w-auto"
        >
          {status.done ? "Review station" : "Station record"}
        </ButtonLink>
      ) : null}
    </div>
  );
}

/**
 * The way to a released result.
 *
 * Whether there is one to read is the server's answer, so this asks rather
 * than deciding from the circuit's status — `released_at` is null until a
 * course lead signs it off, which can be weeks after the sitting ended.
 */
function MyResultLink({ sittingId }: { sittingId: string }) {
  const { hrefFor } = useSurface();
  // A result nobody has released yet answers 404 as readily as one that is
  // not this person's, and neither is a page failure — the link simply is not
  // there. `AsyncBoundary` would turn both into an alert on a screen the
  // candidate came to for something else.
  const state = useAsync(
    (signal) => readMyResult(sittingId, signal).catch(() => null),
    [sittingId],
  );

  if (!state.data?.released_at) return null;

  return (
    <Alert tone="success" title="Your result has been released">
      <TextLink themeType="b2b" href={hrefFor(`/trainee/results/${sittingId}`)}>
        Read your result
      </TextLink>
    </Alert>
  );
}
