"use client";

import type { ReactNode } from "react";
import type { IconType } from "react-icons";
import { HiOutlineInformationCircle } from "react-icons/hi2";
import { cn } from "@/foundation/ui";

const sectionCard =
  "flex min-w-0 flex-col overflow-hidden rounded-osce-lg border border-osce-border bg-osce-surface";

function SectionHeader({ icon: Icon, children }: { icon?: IconType; children: ReactNode }) {
  return (
    <header className="flex items-center gap-2 px-5 pb-1 pt-[18px]">
      {Icon ? <Icon className="h-4 w-4 shrink-0 text-b2c-text-muted" aria-hidden /> : null}
      <h2 className="text-osce-subheading font-semibold text-osce-ink-900">{children}</h2>
    </header>
  );
}

/**
 * The consultation as three cards (canvas `train-room`): the room on the
 * left, the reading in the middle, and live marking ("What you've covered")
 * on the right.
 *
 * The room holds a microphone, a name and one button; the middle holds
 * everything the candidate is actually reading while they talk; the right
 * column shows coverage landing as it is earned, open by default with its own
 * close button. Without a coverage column (review, where there is no live
 * room) the card falls back to the two-fifths / three-fifths split the
 * retiring client used. On a narrow screen the sections stack, dividers turn
 * stack, and the room sticks to the top during an attempt so the End
 * button stays reachable while the brief scrolls.
 *
 * The aside is the caller's: the brief during an attempt, the transcript
 * afterwards. This component owns the frame and nothing else, which is what
 * lets one screen serve both.
 */
export function ConsultationScreen({
  panel,
  aside,
  asideTitle,
  asideIcon,
  sticky = true,
  showTerms = true,
  coverage,
}: {
  panel: ReactNode;
  aside: ReactNode;
  asideTitle: string;
  asideIcon: IconType;
  /** Off in review, where there is no live room to keep within reach. */
  sticky?: boolean;
  showTerms?: boolean;
  coverage?: ReactNode;
}) {
  return (
    <div className="mb-8">
      <div
        className={cn(
          "grid grid-cols-1 gap-4 lg:h-[60vh] lg:min-h-[420px]",
          coverage
            ? "lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.3fr)_minmax(0,0.9fr)]"
            : "lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]",
        )}
      >
        <section
          className={cn(
            sectionCard,
            "min-h-[min(420px,58vh)] lg:min-h-0",
            sticky
              ? "sticky top-0 z-10 max-h-[min(520px,68vh)] lg:static lg:max-h-none"
              : "max-h-none",
          )}
        >
          <SectionHeader>Consultation</SectionHeader>
          <div className="flex min-h-[min(340px,48vh)] flex-1 flex-col justify-between gap-4 overflow-y-auto px-5 pb-5 pt-3 lg:min-h-0 lg:justify-end lg:gap-0">
            {panel}
          </div>
        </section>

        <section className={cn(sectionCard, "min-h-[320px] lg:min-h-0")}>
          <SectionHeader icon={asideIcon}>{asideTitle}</SectionHeader>
          <div className="min-h-0 flex-1 overflow-y-auto">{aside}</div>
        </section>

        {coverage && <section className={cn(sectionCard, "lg:min-h-0")}>{coverage}</section>}
      </div>

      {showTerms && (
        <p className="mt-4 flex items-start justify-center gap-2 px-2 text-osce-meta text-b2c-text-muted lg:items-center">
          <HiOutlineInformationCircle className="mt-0.5 h-4 w-4 shrink-0 lg:mt-0" aria-hidden />
          By starting the consultation you agree to our terms of service.
        </p>
      )}
    </div>
  );
}
