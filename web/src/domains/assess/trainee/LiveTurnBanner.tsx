"use client";

import { HiMiniSignal } from "react-icons/hi2";
import { b2bTokens } from "@/foundation/ui";
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
    <div
      className={`rounded-lg border p-5 ${b2bTokens.b2bSemanticSuccess}`}
    >
      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <span className={`${b2bTokens.b2bIconChipBase} ${b2bTokens.b2bChipHueClasses.green}`}>
            <HiMiniSignal className="h-5 w-5 animate-pulse" aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-osce-body font-semibold">{copy.title}</p>
            <p className="mt-0.5 text-osce-body font-medium opacity-90">
              {sitting.name} · {sitting.circuit_name}
            </p>
            <p className="mt-1 text-osce-body leading-snug text-b2b-mid">{copy.body}</p>
          </div>
        </div>
        <JoinRoom sitting={sitting} />
      </div>
    </div>
  );
}
