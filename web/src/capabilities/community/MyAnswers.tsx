"use client";

import Link from "next/link";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  ModalContent,
  ModalHelper,
  ModalSecondaryButton,
  ModalTitle,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities/SurfaceContext";

/**
 * The answers this person wrote.
 *
 * Nothing on `platform-api` lists one person's replies: replies are read per
 * question, so the only way to assemble this today is a request per question
 * in the feed. The screen is here with its empty state rather than built on a
 * hundred requests — `docs/port-gaps.md` names the endpoint that would fill
 * it, and nothing is silently dropped in the meantime.
 */
export function MyAnswers() {
  const { hrefFor } = useSurface();

  return (
    <ModalContent className="mb-24 max-w-3xl space-y-3">
      <div>
        <ModalTitle>My Answers</ModalTitle>
        <ModalHelper>Answers you have contributed to the community.</ModalHelper>
      </div>

      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>No answers yet</B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-3">
          <p className="text-osce-body text-osce-ink-500">
            You haven&apos;t answered any questions in the community.
          </p>
          <Link href={hrefFor("/discussion")}>
            <ModalSecondaryButton type="button">Explore Questions</ModalSecondaryButton>
          </Link>
        </B2CPanelCardBody>
      </B2CPanelCard>
    </ModalContent>
  );
}
