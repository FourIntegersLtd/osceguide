"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { Alert, AsyncBoundary } from "@/foundation/ui";
import { boardChip } from "@/foundation/ui/boardKit";
import {
  TraineeHead,
  TraineeHero,
  TraineeList,
  TraineePage,
  TraineeRow,
} from "@/domains/assess/trainee/traineeBoard";
import { useAsync } from "@/foundation/hooks";
import { passWord, ratingLabel } from "@/capabilities/feedback/rubric";
import {
  ratingVariant,
  summaryDomains,
} from "@/domains/assess/results/reviewForm";
import {
  readMyReview,
  readMySittings,
  reviewIfReady,
  reviewWaitingCopy,
} from "@/domains/assess/trainee/api";
import { useSurface } from "@/capabilities";
import { byMarker, feedbackLabels, ratingWord } from "@/domains/assess/room/peerMarks";
import { readMyPeerMarks } from "@/domains/assess/room/api";

/**
 * A candidate's own review of one station, once the GP lead has completed
 * one and not before. Mirrors `MyResult`'s release gate: the server decides
 * whether there is anything to show, this screen only renders what came back.
 *
 * Ratings are written in the rubric's own kind (`summary.rating`), so a
 * G / A / R station, a 0-4 station and a met / not met station all read right;
 * domains carry the rubric's own titles (`summary.domain_labels`).
 */
export function MyReview({ slotId }: { slotId: string }) {
  const router = useRouter();
  const state = useAsync((signal) => readMyReview(slotId, signal), [slotId]);
  const { orgSlug } = useSurface();
  // The station and sitting this feedback is for come from the feed the candidate's other screens already read.
  const feed = useAsync((signal) => readMySittings(orgSlug, signal), [orgSlug]);
  const owner = feed.data?.items?.find((sitting) =>
    sitting.slots?.some((slot) => slot.id === slotId),
  );
  const station = owner?.slots?.find(
    (slot) => slot.id === slotId,
  )?.station_title;

  return (
    <TraineePage label="Station feedback">
      <div>
        <Link
          href="#"
          onClick={(event) => {
            event.preventDefault();
            router.back();
          }}
          className="text-assess-label text-osce-accent"
        >
          ‹ Back
        </Link>
      </div>
      <TraineeHead
        eyebrow="Your review"
        title="Station feedback"
        desc={
          owner ? [station, owner.name].filter(Boolean).join(" · ") : undefined
        }
      />

      <AsyncBoundary state={state}>
        {(answer) => {
          const review = reviewIfReady(answer);
          if (review === null) {
            const waiting = reviewWaitingCopy(
              (answer as { state: "not_released" | "not_marked" }).state,
            );
            return (
              <Alert tone="info" title={waiting.title}>
                {waiting.body}
              </Alert>
            );
          }
          const rating = review.summary.rating ?? null;
          const overall = review.summary.overall_rag;
          const outcome = passWord(review.summary.passed);
          const domains = summaryDomains(review.summary);
          return (
            <>
              <TraineeHero
                eyebrow="Overall"
                size="xl"
                title={
                  <>
                    {ratingLabel(rating, overall)}{" "}
                    {outcome ? (
                      <span
                        className={boardChip(
                          review.summary.passed ? "ok" : "live",
                        )}
                      >
                        {outcome}
                      </span>
                    ) : null}
                  </>
                }
              >
                {review.notes ? (
                  <span className="whitespace-pre-wrap">{review.notes}</span>
                ) : null}
              </TraineeHero>

              {domains.length > 0 || review.completed_at ? (
                <TraineeList title="By domain">
                  {domains.map((domain) => (
                    <TraineeRow key={domain.id} title={domain.label}>
                      <span
                        className={boardChip(
                          chipTone(ratingVariant(rating, domain.value)),
                        )}
                      >
                        {ratingLabel(rating, domain.value)}
                      </span>
                    </TraineeRow>
                  ))}
                  {review.completed_at ? (
                    <TraineeRow
                      title={
                        <span className="text-osce-ink-500">
                          Completed{" "}
                          {new Date(review.completed_at).toLocaleString()}
                        </span>
                      }
                    />
                  ) : null}
                </TraineeList>
              ) : null}
              <PeerFeedback
                slotId={slotId}
                labels={(review.summary as { domain_labels?: Record<string, string> }).domain_labels ?? {}}
              />
            </>
          );
        }}
      </AsyncBoundary>
    </TraineePage>
  );
}

function chipTone(variant: string): "ok" | "warn" | "live" | "neutral" {
  return variant === "success"
    ? "ok"
    : variant === "warning"
      ? "warn"
      : variant === "danger"
        ? "live"
        : "neutral";
}

/** What the other trainees in the room marked on this turn, shown once the review is out. Absent when there are none. */
function PeerFeedback({ slotId, labels }: { slotId: string; labels: Record<string, string> }) {
  const state = useAsync((signal) => readMyPeerMarks(slotId, signal), [slotId]);
  const marks = state.data ?? null;
  const items = feedbackLabels(marks, labels);
  const groups = byMarker(marks, items);
  if (groups.length === 0) return null;
  return (
    <TraineeList title="From the room">
      {groups.map((group) => (
        <TraineeRow key={group.markerId} title={group.name}>
          <ul className="m-0 list-none p-0 text-assess-desc text-osce-ink-700">
            {group.rows.map((row) => (
              <li key={row.item}>
                {row.label}{row.rating ? `: ${ratingWord(row.rating)}` : ""}
                {row.comment ? ` · ${row.comment}` : ""}
              </li>
            ))}
          </ul>
        </TraineeRow>
      ))}
    </TraineeList>
  );
}
