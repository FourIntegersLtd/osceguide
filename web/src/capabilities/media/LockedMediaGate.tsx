"use client";

import Link from "next/link";
import { LuLock } from "react-icons/lu";
import { ButtonLink, productTokens as t } from "@/foundation/ui";
import { useSurface } from "@/capabilities/SurfaceContext";
import type { MediaItem } from "@/capabilities/media/api";

/**
 * Shown when `GET /media/{slug}` returns `locked: true`.
 *
 * OpenAI and staff authoring populate the library; a live entitlement opens
 * the body, as does the fourteen-day trial for the account’s registered exam.
 */
export function LockedMediaGate({ item }: { item: MediaItem }) {
  const { hrefFor } = useSurface();
  const exam = item.exam_code?.toUpperCase() ?? "this exam";

  return (
    <section className={`${t.b2cHeroCtaSurface} mt-6`}>
      <span className="flex h-10 w-10 items-center justify-center rounded-control border border-osce-border bg-osce-surface text-osce-ink-600">
        <LuLock className="h-4 w-4" aria-hidden />
      </span>
      <h2 className="mt-4 text-osce-title font-semibold text-osce-ink-900">Upgrade to read this</h2>
      <p className="mt-1.5 max-w-[560px] text-osce-body text-b2c-text-muted">
        This is part of the {exam} study library. Subscribe to unlock slide decks, summaries,
        articles and episodes for your exam.
      </p>
      <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-3">
        <ButtonLink href={`${hrefFor("/settings")}?tab=payments`} variant="primary" size="md">
          View plans
        </ButtonLink>
        <Link href={hrefFor("/settings")} className={`text-osce-meta ${t.b2cLink}`}>
          Already subscribed? Check your access in Settings
        </Link>
      </div>
    </section>
  );
}
