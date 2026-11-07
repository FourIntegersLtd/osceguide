"use client";

import { ActionMenu, Button, ButtonLink, LinkedStepper, type LinkedStep } from "@/foundation/ui";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import {
  circuitReviewSteps,
  nextReviewAction,
  reviewStations,
  type CircuitReviewStepId,
} from "@/domains/assess/sessions/circuitReviewSteps";
import { openRailSection } from "@/domains/assess/sessions/RailSection";
import { slotReviewPath } from "@/domains/assess/sessions/support";

/**
 * What the hero offers once a circuit has ended: the shared connected stepper (mark, share, results),
 * ONE primary action from `nextReviewAction`, and the rest in a menu. Nothing else repeats the stations:
 * the list below is the only one.
 */
export function EndedActions({ data, published }: { data: CircuitConsole; published: boolean }) {
  const { session } = useSession();
  const { hrefFor } = useSurface();
  const canMark = can(session, "sign_off_results");
  const stations = reviewStations(data);
  const { steps, line } = circuitReviewSteps(stations, published);
  const next = nextReviewAction(stations, published);
  const markedAny = stations.some((s) => s.state === "marked");

  const links: Record<CircuitReviewStepId, Pick<LinkedStep, "href" | "onSelect">> = {
    mark: next.kind === "mark" ? { href: hrefFor(slotReviewPath(next.station)) } : {},
    share: { onSelect: () => openRailSection("feedback") },
    results: { href: hrefFor("/results") },
  };
  const linked: LinkedStep<CircuitReviewStepId>[] = steps.map((step) => ({ ...step, ...(canMark ? links[step.id] : {}) }));

  return (
    <LinkedStepper steps={linked} label="What is left" hint={canMark ? line : "Only people who approve results can mark and send feedback."}>
      {canMark ? (
        <>
          {next.kind === "mark" ? (
            <ButtonLink href={hrefFor(slotReviewPath(next.station))} themeType="b2b" variant="commit">
              {next.label}
            </ButtonLink>
          ) : next.kind === "publish" ? (
            <Button themeType="b2b" variant="commit" onClick={() => openRailSection("feedback")}>
              {next.label}
            </Button>
          ) : (
            <ButtonLink href={hrefFor("/results")} themeType="b2b" variant="commit">
              {next.label}
            </ButtonLink>
          )}
          <ActionMenu
            label="More circuit actions"
            items={[
              {
                label: published ? "Change sent feedback" : "Send feedback",
                disabled: !markedAny,
                hint: markedAny ? undefined : "Mark a station first",
                onSelect: () => openRailSection("feedback"),
              },
              { label: "Open results", href: hrefFor("/results") },
              { label: "Changes made during the circuit", onSelect: () => openRailSection("changes") },
              { label: "Transcripts and AI marks", onSelect: () => openRailSection("record") },
            ]}
          />
        </>
      ) : null}
    </LinkedStepper>
  );
}
