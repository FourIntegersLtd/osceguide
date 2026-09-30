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
 * The consultation, as two columns: the room on the left, the reading on the
 * right.
 *
 * Two fifths and three fifths, which is the retiring client's split and the
 * reason it works — the left panel holds a microphone, a name and one button,
 * and the right holds everything the candidate is actually reading while they
 * talk. On a narrow screen they stack and the left one sticks to the top
 * during an attempt, so the End button stays reachable while the brief
 * scrolls.
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
      <div className="flex h-full flex-col gap-6 lg:flex-row lg:gap-8">
        <B2CPanelCard
          className={cn(
            "mt-0 flex min-h-[min(420px,58vh)] w-full flex-col lg:static lg:h-[60vh] lg:min-h-[420px] lg:w-2/5",
            sticky
              ? "sticky top-0 z-10 max-h-[min(520px,68vh)] lg:max-h-none"
              : "max-h-none",
          )}
        >
          <B2CPanelCardHeader>
            <B2CPanelCardHeaderIcon icon={HiOutlineMicrophone} tone="violet" />
            Consultation
          </B2CPanelCardHeader>
          <B2CPanelCardBody className="flex min-h-[min(340px,48vh)] flex-1 flex-col justify-between gap-4 space-y-0 lg:min-h-0 lg:justify-end lg:gap-0">
            {panel}
          </B2CPanelCardBody>
        </B2CPanelCard>

        <B2CPanelCard
          className={cn(
            "mt-0 flex w-full flex-col overflow-hidden lg:h-[60vh] lg:min-h-[420px] lg:w-3/5",
            sticky && "h-[60vh] min-h-[420px]",
          )}
        >
          <B2CPanelCardHeader>
            <B2CPanelCardHeaderIcon icon={asideIcon} tone={asideTone} />
            {asideTitle}
          </B2CPanelCardHeader>
          <div className="min-h-0 flex-1 overflow-y-auto">{aside}</div>
          {coverage}
        </B2CPanelCard>
      </div>

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
