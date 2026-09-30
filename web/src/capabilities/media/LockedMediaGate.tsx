"use client";

import Link from "next/link";
import { LuLock } from "react-icons/lu";
import { B2CPanelCard, B2CPanelCardBody, ButtonLink, productTokens as t } from "@/foundation/ui";
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
    <B2CPanelCard className="mt-6">
      <B2CPanelCardBody className="flex flex-col items-center px-6 py-10 text-center sm:px-10">
        <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-b2c-surface-muted text-osce-ink-600">
          <LuLock className="h-5 w-5" aria-hidden />
        </span>
        <h2 className={t.b2cSectionTitle}>Upgrade to read this</h2>
        <p className={`mt-2 max-w-md ${t.b2cBodyTextMuted}`}>
          {item.title} is part of the {exam} study library. Subscribe to unlock slide decks,
          summaries, articles and episodes for your exam.
        </p>
        <ButtonLink
          href={`${hrefFor("/settings")}?tab=payments`}
          variant="primary"
          size="md"
          className="mt-6"
        >
          View plans
        </ButtonLink>
        <p className="mt-4 text-osce-meta text-b2c-text-muted">
          Already subscribed?{" "}
          <Link href={hrefFor("/settings")} className={t.b2cLink}>
            Check your access in Settings
          </Link>
        </p>
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}
