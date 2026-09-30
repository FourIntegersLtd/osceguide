"use client";

import type { ReactNode } from "react";
import type { IconType } from "react-icons";
import { HiInformationCircle, HiOutlineMicrophone } from "react-icons/hi2";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  B2CPanelCardHeaderIcon,
  cn,
  type B2CSectionIconTone,
} from "@/foundation/ui";

/**
 * The consultation as one card of three sections: the room on the left, the
 * reading in the middle, and live marking ("What you've covered") on the
 * right, each separated by a hairline divider rather than sitting in its own
 * card.
 *
 * The room holds a microphone, a name and one button; the middle holds
 * everything the candidate is actually reading while they talk; the right
 * column shows coverage landing as it is earned, open by default with its own
 * close button. Without a coverage column (review, where there is no live
 * room) the card falls back to the two-fifths / three-fifths split the
 * retiring client used. On a narrow screen the sections stack, dividers turn
 * horizontal, and the room sticks to the top during an attempt so the End
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
  asideTone = "primary",
  sticky = true,
  showTerms = true,
  coverage,
}: {
  panel: ReactNode;
  aside: ReactNode;
  asideTitle: string;
  asideIcon: IconType;
  asideTone?: B2CSectionIconTone;
  /** Off in review, where there is no live room to keep within reach. */
  sticky?: boolean;
  showTerms?: boolean;
  coverage?: ReactNode;
}) {
  return (
    <div className="mb-8 lg:h-[75vh]">
      <B2CPanelCard className="mt-0 flex w-full flex-col lg:h-[60vh] lg:min-h-[420px] lg:flex-row">
        <section
          className={cn(
            "flex min-h-[min(420px,58vh)] w-full flex-col border-b border-b2c-border bg-osce-surface lg:min-h-0 lg:border-b-0 lg:border-r",
            coverage ? "lg:w-[30%]" : "lg:w-2/5",
            sticky
              ? "sticky top-0 z-10 max-h-[min(520px,68vh)] lg:static lg:max-h-none"
              : "max-h-none",
          )}
        >
          <B2CPanelCardHeader>
            <B2CPanelCardHeaderIcon icon={HiOutlineMicrophone} tone="violet" />
            Consultation
          </B2CPanelCardHeader>
          <B2CPanelCardBody className="flex min-h-[min(340px,48vh)] flex-1 flex-col justify-between gap-4 space-y-0 overflow-y-auto lg:min-h-0 lg:justify-end lg:gap-0">
            {panel}
          </B2CPanelCardBody>
        </section>

        <section
          className={cn(
            "flex min-h-[320px] w-full flex-col overflow-hidden lg:min-h-0",
            coverage
              ? "border-b border-b2c-border lg:w-[42%] lg:border-b-0 lg:border-r"
              : "lg:w-3/5",
          )}
        >
          <B2CPanelCardHeader>
            <B2CPanelCardHeaderIcon icon={asideIcon} tone={asideTone} />
            {asideTitle}
          </B2CPanelCardHeader>
          <div className="min-h-0 flex-1 overflow-y-auto">{aside}</div>
        </section>

        {coverage && (
          <section className="flex w-full flex-col overflow-hidden lg:min-h-0 lg:w-[28%]">
            {coverage}
          </section>
        )}
      </B2CPanelCard>

      {showTerms && (
        <div className="mb-12 mt-6 flex items-start justify-center gap-2 px-2 lg:items-center">
          <HiInformationCircle className="mt-0.5 h-5 w-5 shrink-0 text-osce-accent lg:mt-0" aria-hidden />
          <p className="text-center text-osce-body text-b2c-text-muted lg:text-left">
            By clicking on the &ldquo;Start Consultation&rdquo; button, you confirm that you agree
            to our terms of Service
          </p>
        </div>
      )}
    </div>
  );
}
