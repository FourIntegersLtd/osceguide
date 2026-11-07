"use client";

import Link from "next/link";
import {
  Alert,
  AsyncBoundary,
  Button,
  ButtonLink,
  EmptyState,
  TextLink,
} from "@/foundation/ui";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { plural } from "@/foundation/format";
import { useSurface } from "@/capabilities";
import { useMicPreflight } from "@/foundation/livekit";
import { JoinRoom } from "@/domains/assess/trainee/JoinRoom";
import { SlotReadingBrief } from "@/domains/assess/trainee/SlotReadingBrief";
import { TrainingRoom } from "@/domains/assess/trainee/TrainingRoom";
import {
  mySittingsStreamPath,
  readMyResult,
  readMyReview,
  readMySittings,
  reviewIfReady,
  type MySitting,
  type MySittings,
  type MySlot,
} from "@/domains/assess/trainee/api";
import {
  activeSlot,
  isExam,
  candidateDone,
  modeLabel,
  orderedSlots,
  progressOf,
  slotStatus,
} from "@/domains/assess/trainee/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";
import { b2bTokens as t } from "@/foundation/ui";
import { boardPad, boardChip } from "@/foundation/ui/boardKit";
import {
  TraineeHead,
  TraineeHero,
  TraineeList,
  TraineePage,
  TraineeRow,
} from "@/domains/assess/trainee/traineeBoard";
import { whenWords } from "@/domains/assess/trainee/support";

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
  const w = useAssessWords();
  const { orgSlug } = useSurface();
  const initial = useAsync(
    (signal) => readMySittings(orgSlug, signal),
    [orgSlug],
  );
  const stream = useEventStream<MySittings>(mySittingsStreamPath(orgSlug));
  const data = stream.data ?? initial.data;
  const mine = (data?.items ?? []).filter(
    (sitting) => sitting.id === sittingId,
  );

  return (
    <TraineePage label="Your sitting">
      <AsyncBoundary
        state={initial}
        isEmpty={() => mine.length === 0}
        empty={{
          title: `We could not find that ${w.sitting}`,
          description:
            "You may have been taken off it, or it belongs to another organisation.",
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
    </TraineePage>
  );
}

/** Ask for the microphone before the room opens, so a blocked browser is found now and not at the door. */
function MicCheck() {
  const mic = useMicPreflight();
  const ok = mic.status === "ready";
  return (
    <div className={boardPad}>
      <h2 className="text-assess-desc font-semibold">Check your microphone</h2>
      <div className={t.assessMeta}>
        {ok
          ? "Your microphone is ready."
          : mic.status === "denied"
            ? "Your browser blocked the microphone. Allow it in the address bar, then try again."
            : mic.status === "missing"
              ? "No microphone was found. Connect one, then try again."
              : "We check it before you join. Allow it in the address bar, then try again."}
      </div>
      {ok ? null : (
        <Button
          themeType="b2b"
          variant="secondary"
          size="sm"
          className="self-start"
          onClick={() => void mic.request()}
        >
          Test microphone
        </Button>
      )}
    </div>
  );
}

function Circuit({ sitting }: { sitting: MySitting }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const slots = orderedSlots(sitting);
  const briefSlot = readingBriefSlot(sitting);
  const { total } = progressOf(sitting);
  const exam = isExam(sitting);
  // Once the sitting is over there is nothing to join or prepare for: the stations and the result are what is left.
  const over = candidateDone(sitting);

  return (
    <>
      <div>
        <Link
          href={hrefFor("/trainee")}
          className="text-assess-label text-osce-accent"
        >
          ‹ All {w.sittings}
        </Link>
      </div>
      <TraineeHead
        eyebrow={
          sitting.scheduled_for
            ? whenWords(sitting.scheduled_for) || modeLabel(sitting)
            : modeLabel(sitting)
        }
        title={sitting.name}
        desc={`${exam ? "Formal exam" : "Practice circuit"} · ${plural(total, "station")}`}
        acts={
          <>
            {sitting.live ? (
              <span className={boardChip("ok")}>Live</span>
            ) : null}
            {sitting.paused ? (
              <span className={boardChip("warn")}>Paused</span>
            ) : null}
          </>
        }
      />

      {sitting.can_join || over ? null : (
        <Alert
          tone="info"
          title={exam ? "Before you start" : "How a practice circuit works"}
        >
          {exam
            ? "Your station opens when your supervisor starts it. Go in straight away: the patient joins when reading time ends, and you need to be in the room by then."
            : "Your supervisor opens the room. Only the person whose turn it is speaks with the patient. Each station's review appears here as soon as your supervisor completes it."}
        </Alert>
      )}

      {sitting.can_join || over ? null : <MicCheck />}

      {sitting.can_join && !exam ? <TrainingRoom sitting={sitting} /> : null}

      {sitting.can_join && exam ? (
        <TraineeHero
          live
          size="md"
          eyebrow={
            activeSlot(sitting) && total > 0
              ? `${exam ? "Station" : "Turn"} ${activeSlot(sitting)!.slot_index + 1} of ${total}`
              : "Today"
          }
          title={exam ? "Your station is open" : "Your turn is live"}
          action={<JoinRoom sitting={sitting} />}
        >
          {activeSlot(sitting)?.station_title ?? null}
        </TraineeHero>
      ) : null}

      {briefSlot?.status === "reading" ? (
        <Alert tone="info" title="Joining during reading">
          You join automatically while you read, so the patient is ready when it
          starts.
        </Alert>
      ) : null}

      {briefSlot && !(sitting.can_join && !exam) ? <SlotReadingBrief slot={briefSlot} /> : null}

      {slots.length === 0 ? (
        <EmptyState
          title="Nothing assigned yet"
          description="Your stations will appear here once your organiser adds them."
        />
      ) : (
        <TraineeList title={exam ? "Your stations" : "Your turns"}>
          {slots.map((slot) => (
            <Slot key={slot.id} slot={slot} exam={exam} />
          ))}
        </TraineeList>
      )}

      <MyResultLink sittingId={sitting.id} />
    </>
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
    <TraineeRow
      title={`${exam ? "Station" : "Turn"} ${slot.slot_index + 1}${slot.station_title ? ` · ${slot.station_title}` : ""}`}
      meta={
        slot.marking_failed
          ? "This station could not be marked automatically. Your school has been told and will mark it for you."
          : status.done
            ? "Read this one back below. A finished station cannot be re-entered."
            : undefined
      }
    >
      <span
        className={boardChip(
          status.done ? "ok" : slot.is_active ? "info" : "neutral",
        )}
      >
        {slot.is_active && !status.done ? "Now" : status.label}
      </span>
      {slot.attempt_id ? (
        <ButtonLink
          themeType="b2b"
          variant="secondary"
          size="sm"
          href={hrefFor(`/attempts/${slot.attempt_id}`)}
        >
          {status.done ? "Review station" : "Station record"}
        </ButtonLink>
      ) : null}
      {status.done ? <MyReviewLink slotId={slot.id} /> : null}
    </TraineeRow>
  );
}

/**
 * The way to this station's feedback, shown only once the server says there
 * is some to read (the result released and a GP lead review completed).
 */
function MyReviewLink({ slotId }: { slotId: string }) {
  const { hrefFor } = useSurface();
  // Not yet readable answers null — no link.
  const state = useAsync((signal) => readMyReview(slotId, signal), [slotId]);

  // A failed check is said, not hidden: no link and no reason reads as "there is no feedback".
  if (state.error)
    return (
      <span className="text-osce-meta text-b2b-mid">
        Could not check for feedback. Reload to try again.
      </span>
    );
  if (!state.data || !reviewIfReady(state.data)) return null;

  return (
    <ButtonLink
      themeType="b2b"
      variant="secondary"
      size="sm"
      href={hrefFor(`/trainee/reviews/${slotId}`)}
    >
      Station feedback
    </ButtonLink>
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
  // Nothing released yet (or not this person's) answers null — the link
  // simply is not there.
  const state = useAsync(
    (signal) => readMyResult(sittingId, signal),
    [sittingId],
  );

  if (state.error)
    return (
      <Alert tone="warning">
        Could not check whether your result is released. Reload to try again.
      </Alert>
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

/**
 * The slot a candidate should see the reading brief for, if any.
 *
 * The active slot during reading — either the server has dispatched an attempt
 * (and the brief comes from `GET /attempts/{id}/brief`) or it has not (and the
 * brief comes from the org station list). A sitting between stations has no
 * active slot, and a finished station has no brief to show.
 */
function readingBriefSlot(sitting: MySitting): MySlot | null {
  const active = activeSlot(sitting);
  if (!active) return null;
  if (active.status === "completed" || active.exam_completed_at) return null;
  return active;
}
