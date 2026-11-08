"use client";

import { ButtonLink } from "@/foundation/ui/ButtonLink";
import { useSurface } from "@/capabilities";
import { JoinRoom } from "@/domains/assess/trainee/JoinRoom";
import type { MySitting } from "@/domains/assess/trainee/api";
import { isExam, liveBannerCopy, liveRooms, liveTitle } from "@/domains/assess/trainee/support";
import { liveCopy } from "@/domains/assess/trainee/hireCopy";
import { useAssessWords } from "@/capabilities/assess-words";
import { TraineeHero } from "@/domains/assess/trainee/traineeBoard";

/**
 * The one thing on the page when a station is open for this person.
 *
 * It carries the room rather than a link to it: the candidate has to be *in*
 * the LiveKit room before the reading phase ends or the patient dispatch finds
 * nothing to join, and a banner that only navigates loses that race on a slow
 * page. Everything else on the overview can wait behind this.
 */
export function LiveTurnBanner({
  sittings,
}: {
  sittings: readonly MySitting[];
}) {
  if (sittings.length === 0) return null;
  const { embedded, linked } = liveRooms(sittings);

  return (
    <section
      aria-label={
        sittings.length === 1 ? "Live consultation" : "Live consultations"
      }
      className="flex flex-col gap-3"
    >
      <h2 className="sr-only">Live now</h2>
      {embedded ? <LiveCard sitting={embedded} embed /> : null}
      {linked.map((sitting) => (
        <LiveCard key={`${sitting.id}-${sitting.circuit_id}`} sitting={sitting} />
      ))}
    </section>
  );
}

/** The circuit name only when it says something the sitting name does not. */
function whereLine(sitting: MySitting): string {
  return sitting.circuit_name && sitting.circuit_name !== sitting.name
    ? `${sitting.name} · ${sitting.circuit_name}`
    : sitting.name;
}

function LiveCard({
  sitting,
  embed = false,
}: {
  sitting: MySitting;
  embed?: boolean;
}) {
  const { hrefFor } = useSurface();
  const w = useAssessWords();
  // An employer's candidate is told their assessor is ready, and joins by station.
  const hire = w.hiring && isExam(sitting) ? liveCopy(sitting) : null;
  const copy = hire ?? liveBannerCopy(sitting);

  return (
    <TraineeHero
      live
      eyebrow={hire ? "Now" : "Today"}
      title={hire ? hire.title : liveTitle(sitting)}
      action={
        embed ? (
          <JoinRoom sitting={sitting} label={hire?.join} />
        ) : (
          <ButtonLink
            href={hrefFor(`/trainee/sittings/${sitting.id}`)}
            themeType="b2b"
            variant="commit"
          >
            Open the room
          </ButtonLink>
        )
      }
    >
      {hire ? copy.body : `${whereLine(sitting)}. ${copy.body}`}
    </TraineeHero>
  );
}
