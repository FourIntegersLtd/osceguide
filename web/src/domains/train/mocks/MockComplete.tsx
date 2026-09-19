"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { LuTrophy } from "react-icons/lu";
import { HiArrowRight } from "react-icons/hi";
import { HiOutlinePlus } from "react-icons/hi2";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  Confetti,
  cn,
  productTokens,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import type { StationSet } from "@/domains/train/api";
import { checkMilestone } from "@/domains/train/mocks/model";
import type { StationRow } from "@/domains/train/mocks/MockStationsTable";

const PREVIOUS_COUNT_KEY = "prev_station_count";

/**
 * What a candidate sees when the last station in a session is done.
 *
 * The retiring client gave this its own route, `/mocks/[mockId]/complete`, and
 * the runner redirected there — which meant reloading the page after a session
 * put you back on a congratulations screen for work you finished yesterday.
 * It is a state of the session here: the set carries `completed_at`, so the
 * panel appears exactly while the session is finished and the stations below
 * it stay reachable.
 */
export function MockComplete({
  set,
  rows,
  stationsCompleted,
}: {
  set: StationSet;
  rows: StationRow[];
  /** Attempts this person has evaluated across every exam, for the badges. */
  stationsCompleted: number;
}) {
  const router = useRouter();
  const { hrefFor } = useSurface();
  const [showConfetti, setShowConfetti] = useState(false);
  const [achievement, setAchievement] = useState({ title: "", message: "" });
  const celebrated = useRef(false);

  const badgeCount = checkMilestone(stationsCompleted, 0).stationBadges;

  useEffect(() => {
    if (celebrated.current || stationsCompleted === 0) return;
    celebrated.current = true;

    let previous = 0;
    try {
      previous = Number.parseInt(window.localStorage.getItem(PREVIOUS_COUNT_KEY) ?? "0", 10) || 0;
    } catch {
      // A browser with storage blocked simply never celebrates twice.
    }

    const { reached } = checkMilestone(stationsCompleted, previous);
    if (!reached) return;

    setAchievement({
      title: "NEW MILESTONE UNLOCKED!",
      message: `You've completed ${stationsCompleted} stations! (${checkMilestone(stationsCompleted, 0).stationBadges} badges)`,
    });
    setShowConfetti(true);
    try {
      window.localStorage.setItem(PREVIOUS_COUNT_KEY, String(stationsCompleted));
    } catch {
      // ignore
    }
  }, [stationsCompleted]);

  return (
    <div className="w-full py-6 sm:py-8">
      <Confetti
        isActive={showConfetti}
        title={achievement.title}
        message={achievement.message}
        badgeCount={badgeCount}
        onClose={() => setShowConfetti(false)}
      />

      <B2CPanelCard className="mt-0">
        <B2CPanelCardBody className="space-y-5 p-5 sm:p-6">
          <div className="space-y-2">
            <p className={productTokens.b2cEyebrow}>Session completed</p>
            <h2
              className={cn(
                productTokens.b2cPageTitle,
                "inline-flex items-center gap-2.5 text-osce-heading",
              )}
            >
              <LuTrophy
                className="h-7 w-7 shrink-0 text-osce-accent sm:h-8 sm:w-8"
                aria-hidden
              />
              Well done
            </h2>
            <p className="max-w-md text-osce-body text-b2c-text-muted">
              Review this session while it&apos;s fresh, then keep the momentum going.
            </p>
          </div>

          {rows.length > 0 && (
            <ul
              aria-label="Station outcomes"
              className="space-y-2 border-t border-b2c-border pt-4"
            >
              {rows.map((row, index) => (
                <li
                  key={row.entry.id}
                  className="flex flex-wrap items-center justify-between gap-2 text-osce-body text-b2c-text-secondary"
                >
                  <span className="min-w-0 truncate">{`Station ${index + 1}: ${row.title}`}</span>
                  <span className="text-osce-meta text-b2c-text-muted">
                    {row.entry.attempts === 0
                      ? "Not attempted"
                      : `${row.entry.attempts} attempt${row.entry.attempts === 1 ? "" : "s"}`}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {(stationsCompleted > 0 || badgeCount > 0) && (
            <div className="flex flex-wrap gap-x-6 gap-y-2 border-t border-b2c-border pt-4 text-osce-body">
              <p className="text-b2c-text-secondary">
                <span className="font-semibold tabular-nums text-osce-ink-900">
                  {stationsCompleted}
                </span>{" "}
                stations completed
              </p>
              <p className="text-b2c-text-secondary">
                <span className="font-semibold tabular-nums text-osce-ink-900">{badgeCount}</span>{" "}
                milestone badges
              </p>
            </div>
          )}
        </B2CPanelCardBody>
        <B2CPanelCardFooter>
          <button
            type="button"
            onClick={() => router.push(hrefFor("/mocks"))}
            className={cn(productTokens.b2cGhostButton, "justify-center gap-2")}
          >
            <HiOutlinePlus className="h-4 w-4" aria-hidden />
            New session
          </button>
          <button
            type="button"
            onClick={() => router.push(hrefFor(`/mocks/${set.id}`))}
            className={cn(productTokens.b2cButtonPrimary, "justify-center gap-2")}
          >
            Review session
            <HiArrowRight className="h-4 w-4" aria-hidden />
          </button>
        </B2CPanelCardFooter>
      </B2CPanelCard>
    </div>
  );
}
