"use client";

import type { ReactNode } from "react";
import type { IconType } from "react-icons";
import { HiOutlineInformationCircle } from "react-icons/hi2";
import { useLocalPreference } from "@/foundation/hooks";
import { cn } from "@/foundation/ui";
import { b2cRoomFill } from "@/foundation/ui/productTokens";
import { LiveSideTabs } from "@/capabilities/attempt-runner/consultation/LiveSideTabs";
import { showCameraLine, sideTab, type SideTab } from "@/capabilities/attempt-runner/consultation/sideTabPreference";
import { liveCoverageHidden } from "@/capabilities/attempt-runner/coverage/preference";
import { TurnOff } from "@/capabilities/attempt-runner/nonverbal/NonverbalCuesPanel";
import { AlertDot } from "./AlertDot";

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
  cues,
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
  /** Live non-verbal cues. With `coverage`, the right-hand column becomes a "Covered" | "Live cues" switch; without, the layout is unchanged. `cameraOn` + `onTurnOff`: the camera runs, so a collapsed column still shows that and a way to stop it. `alert`: a warning cue is active (a dot shows while "Covered" is showing); `defaultTab` shows until the candidate chooses. */
  cues?: { panel: ReactNode; alert: boolean; defaultTab: SideTab; cameraOn: boolean; onTurnOff: () => void };
  /** The live room: from `lg`, take all the height the page gives it instead of 60vh (below that the room scrolls); and put the consultation card on the dark stage skin. */
  fill?: boolean;
}) {
  const coverageHidden = useLocalPreference(liveCoverageHidden);
  const collapsed = Boolean(coverage) && coverageHidden;
  const chosenTab = useLocalPreference(sideTab);
  const cameraLine = showCameraLine({ cameraOn: Boolean(cues?.cameraOn), collapsed, tab: chosenTab ?? cues?.defaultTab ?? "covered" });
  return (
    <div className={cn(fill ? b2cRoomFill : "mb-8")}>
      {/* Hidden, live marking shrinks to a button above the cards, so the two
          cards take the full width; reopened, it takes its column back. */}
      {collapsed && (
        <div className="relative mb-3 flex justify-end">
          {coverage}
          {cues?.alert && <AlertDot className="absolute -right-1 -top-1 h-2.5 w-2.5" />}
        </div>
      )}
      {cameraLine && cues && (
        <p role="status" className="mb-3 flex items-center justify-end gap-3 text-osce-meta text-b2c-text-muted">
          Camera on for cues
          <TurnOff onClick={cues.onTurnOff} />
        </p>
      )}
      <div
        className={cn(
          "grid grid-cols-1 overflow-hidden border border-osce-border bg-osce-surface lg:min-h-[420px]",
          fill ? "lg:min-h-0 lg:flex-1" : "lg:h-[60vh]",
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

        {coverage && !collapsed && (
          <section className={cn(sectionCard, sectionDivider, "lg:min-h-0")}>
            {cues ? <LiveSideTabs coverage={coverage} cues={cues.panel} alert={cues.alert} defaultTab={cues.defaultTab} /> : coverage}
          </section>
        )}
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
