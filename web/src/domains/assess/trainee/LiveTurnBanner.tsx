"use client";

import { B2CHero, Badge } from "@/foundation/ui";
import { JoinRoom } from "@/domains/assess/trainee/JoinRoom";
import type { MySitting } from "@/domains/assess/trainee/api";
import { liveBannerCopy } from "@/domains/assess/trainee/support";

/**
 * The one thing on the page when a station is open for this person.
 *
 * It carries the room rather than a link to it: the candidate has to be *in*
 * the LiveKit room before the reading phase ends or the patient dispatch finds
 * nothing to join, and a banner that only navigates loses that race on a slow
 * page. Everything else on the overview can wait behind this.
 */
export function LiveTurnBanner({ sittings }: { sittings: readonly MySitting[] }) {
  if (sittings.length === 0) return null;

  return (
    <section
      aria-label={sittings.length === 1 ? "Live consultation" : "Live consultations"}
      className="space-y-3"
    >
      <h2 className="sr-only">Live now</h2>
      {sittings.map((sitting) => (
        <LiveCard key={`${sitting.id}-${sitting.circuit_id}`} sitting={sitting} />
      ))}
    </section>
  );
}

function LiveCard({ sitting }: { sitting: MySitting }) {
  const copy = liveBannerCopy(sitting);

  return (
    <B2CHero
      eyebrow="Today"
      title={copy.title}
      action={<JoinRoom sitting={sitting} />}
      aside={
        <Badge variant="success" dot>
          Live
        </Badge>
      }
    >
      {`${sitting.name} · ${sitting.circuit_name}. ${copy.body}`}
    </B2CHero>
  );
}
