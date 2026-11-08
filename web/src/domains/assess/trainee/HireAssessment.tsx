"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Alert, Button } from "@/foundation/ui";
import { b2bTokens as t, cn } from "@/foundation/ui";
import { boardChip, boardPad } from "@/foundation/ui/boardKit";
import { useAssessWords } from "@/capabilities/assess-words";
import { useSurface } from "@/capabilities";
import { JoinRoom } from "@/domains/assess/trainee/JoinRoom";
import { SlotReadingBrief } from "@/domains/assess/trainee/SlotReadingBrief";
import type { MySitting, MySlot } from "@/domains/assess/trainee/api";
import {
  BRIEF_HINT,
  assessmentDesc,
  finishedCopy,
  readyCopy,
  stationRail,
  waitCopy,
} from "@/domains/assess/trainee/hireCopy";
import { candidateDone } from "@/domains/assess/trainee/support";
import { TraineeHead, TraineeHero } from "@/domains/assess/trainee/traineeBoard";

/**
 * One assessment, as an employer's candidate sees it (HireCandidateAssessment): the station rail, the brief of the
 * station that is open, then either the one Join (live) or a disabled Join with the reason beneath it, or "You have
 * finished". The same feed and the same `can_join` as the institution screen; only the words and the stripped-back
 * layout differ.
 */
export function HireAssessment({
  sitting,
  org,
  briefSlot,
  resultLink,
}: {
  sitting: MySitting;
  org: string;
  briefSlot: MySlot | null;
  resultLink: ReactNode;
}) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const over = candidateDone(sitting);
  const rail = stationRail(sitting);
  const wait = waitCopy(sitting);
  const ready = readyCopy(sitting);
  const done = finishedCopy(org);

  return (
    <>
      <div>
        <Link href={hrefFor("/trainee")} className="text-assess-label text-osce-accent">
          {w.MyTraining}
        </Link>
      </div>
      <TraineeHead
        title={sitting.name}
        desc={assessmentDesc(sitting)}
        acts={sitting.paused ? <span className={boardChip("warn")}>Paused</span> : null}
      />

      {over ? (
        <Alert tone="success" title={done.title}>
          {done.body}
        </Alert>
      ) : (
        <>
          {rail.length > 0 ? (
            <ol aria-label="Your stations" className="m-0 flex list-none flex-wrap gap-2 p-0">
              {rail.map((item) => (
                <li
                  key={item.id}
                  aria-current={item.now ? "step" : undefined}
                  className={cn(
                    "rounded-panel border px-3 py-1.5 text-assess-label",
                    item.now ? "border-osce-accent bg-osce-accent-muted/40 font-semibold" : "border-osce-border bg-osce-surface",
                  )}
                >
                  {item.label}
                </li>
              ))}
            </ol>
          ) : null}

          {briefSlot ? (
            <>
              <SlotReadingBrief slot={briefSlot} />
              <p className={t.assessMeta}>{BRIEF_HINT}</p>
            </>
          ) : (
            <div className={boardPad}>
              <h2 className="text-assess-desc font-semibold">Your briefs</h2>
              <div className={t.assessMeta}>{BRIEF_HINT}</div>
            </div>
          )}

          {sitting.can_join ? (
            <TraineeHero
              live
              size="md"
              eyebrow={ready.eyebrow}
              title={ready.title}
              action={<JoinRoom sitting={sitting} label={ready.join} />}
            >
              {ready.body}
            </TraineeHero>
          ) : (
            <>
              <TraineeHero
                size="md"
                eyebrow={wait.eyebrow}
                title={wait.title}
                action={
                  <Button themeType="b2b" variant="commit" disabled>
                    {wait.join}
                  </Button>
                }
              >
                {wait.body}
              </TraineeHero>
              <p className={cn(t.assessMeta, "m-0 text-right")}>{wait.why}</p>
            </>
          )}
        </>
      )}

      {resultLink}
    </>
  );
}
