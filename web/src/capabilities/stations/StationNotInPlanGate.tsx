"use client";

import Link from "next/link";
import { LuLock } from "react-icons/lu";
import { ButtonLink, productTokens as t } from "@/foundation/ui";
import { useSurface } from "@/capabilities/SurfaceContext";

/**
 * Shown when a library station answers `station_not_in_plan`: a reachable id — from a
 * bookmark, a shared link, or a review a candidate already sat — that falls outside the
 * window this person's paid plan currently unlocks.
 *
 * Mirrors `LockedMediaGate`'s shape rather than the generic `AsyncBoundary` error panel,
 * because the backend's own message ("Upgrade to unlock it") is an instruction, not just
 * a reason, and deserves a button rather than a "Try again" that would only fail again.
 */
export function StationNotInPlanGate() {
  const { hrefFor } = useSurface();

  return (
    <section className={`${t.b2cHeroCtaSurface} mt-6`}>
      <span className="flex h-10 w-10 items-center justify-center rounded-control border border-osce-border bg-osce-surface text-osce-ink-600">
        <LuLock className="h-4 w-4" aria-hidden />
      </span>
      <h2 className="mt-4 text-osce-title font-semibold text-osce-ink-900">Upgrade to unlock this station</h2>
      <p className="mt-1.5 max-w-[560px] text-osce-body text-b2c-text-muted">
        This station is not included in your current plan. A higher plan unlocks more of the
        library.
      </p>
      <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-3">
        <ButtonLink href={`${hrefFor("/settings")}?tab=payments`} variant="primary" size="md">
          Upgrade to Pro
        </ButtonLink>
        <Link href={hrefFor("/settings")} className={`text-osce-meta ${t.b2cLink}`}>
          Already subscribed? Check your access in Settings
        </Link>
      </div>
    </section>
  );
}
