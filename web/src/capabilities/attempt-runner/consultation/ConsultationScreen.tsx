"use client";

import { useSyncExternalStore, type ReactNode } from "react";
import type { IconType } from "react-icons";
import { HiOutlineInformationCircle } from "react-icons/hi2";
import { cn } from "@/foundation/ui";
import {
  getLiveCoverageHidden,
  getLiveCoverageHiddenOnServer,
  subscribeLiveCoverageHidden,
} from "@/capabilities/attempt-runner/coverage/preference";

const sectionCard = "flex min-w-0 flex-col overflow-hidden bg-osce-surface";
/** Sections share one frame; a divider sits above each on a narrow screen and to its left on a wide one. */
const sectionDivider = "border-t border-osce-border lg:border-l lg:border-t-0";

function SectionHeader({ icon: Icon, children }: { icon?: IconType; children: ReactNode }) {
  return (
    <header className="flex items-center gap-2 px-5 pb-1 pt-[18px]">
      {Icon ? <Icon className="h-4 w-4 shrink-0 text-b2c-text-muted" aria-hidden /> : null}
      <h2 className="text-osce-subheading font-semibold text-osce-ink-900">{children}</h2>
    </header>
  );
}

/**
 * The consultation as one square-cornered card split by dividers (canvas
 * `train-room`): the room on the left, the reading in the middle at the same
 * width, and live marking ("What you've covered") in a narrower column on the
 * right.
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
  fill = false,
}: {
  panel: ReactNode;
  aside: ReactNode;
  asideTitle: string;
  asideIcon: IconType;
  /** Off in review, where there is no live room to keep within reach. */
  sticky?: boolean;
  showTerms?: boolean;
  coverage?: ReactNode;
  /** The live room: take all the height the page gives it instead of 60vh, and put the consultation card on the dark stage skin. */
  fill?: boolean;
}) {
  const coverageHidden = useSyncExternalStore(
    subscribeLiveCoverageHidden,
    getLiveCoverageHidden,
    getLiveCoverageHiddenOnServer,
  );
  const collapsed = Boolean(coverage) && coverageHidden;
  return (
    <div className={cn(fill ? "flex min-h-0 flex-1 flex-col" : "mb-8")}>
      {/* Hidden, live marking shrinks to a button above the cards, so the two
          cards take the full width; reopened, it takes its column back. */}
      {collapsed && <div className="mb-3 flex justify-end">{coverage}</div>}
      <div
        className={cn(
          "grid grid-cols-1 overflow-hidden border border-osce-border bg-osce-surface lg:min-h-[420px]",
          fill ? "min-h-0 flex-1" : "lg:h-[60vh]",
          coverage && !collapsed
            ? "lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.6fr)]"
            : "lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]",
        )}
      >
        <section
          data-skin={fill ? "room" : undefined}
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

        <section className={cn(sectionCard, sectionDivider, "min-h-[320px] lg:min-h-0")}>
          <SectionHeader icon={asideIcon}>{asideTitle}</SectionHeader>
          <div className="min-h-0 flex-1 overflow-y-auto">{aside}</div>
        </section>

        {coverage && !collapsed && <section className={cn(sectionCard, sectionDivider, "lg:min-h-0")}>{coverage}</section>}
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
