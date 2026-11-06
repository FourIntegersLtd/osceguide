"use client";

import { JoinRoom } from "@/domains/assess/trainee/JoinRoom";
import type { MySitting } from "@/domains/assess/trainee/api";
import { liveBannerCopy } from "@/domains/assess/trainee/support";
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

  return (
    <section
      aria-label={
        sittings.length === 1 ? "Live consultation" : "Live consultations"
      }
      className="flex flex-col gap-3"
    >
      <h2 className="sr-only">Live now</h2>
      {sittings.map((sitting) => (
        <LiveCard
          key={`${sitting.id}-${sitting.circuit_id}`}
          sitting={sitting}
        />
      ))}
    </section>
  );
}

function LiveCard({ sitting }: { sitting: MySitting }) {
  const copy = liveBannerCopy(sitting);

  return (
    <TraineeHero
      live
      eyebrow="Today"
      title={copy.title}
      action={<JoinRoom sitting={sitting} />}
    >
      {`${sitting.name} · ${sitting.circuit_name}. ${copy.body}`}
    </TraineeHero>
  );
}
