"use client";

import { useCallback, useMemo, useState } from "react";
import { HiChevronRight, HiOutlineSparkles } from "react-icons/hi2";
import { Alert, AsyncBoundary, ButtonLink, b2bTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { AttemptRunner, createAttempt } from "@/capabilities/attempt-runner";
import { listExams, type Exam } from "@/capabilities/stations";
import { listOrgStations, type OrgStation } from "@/domains/assess/trainee/api";
import { practisable, readingBrief } from "@/domains/assess/trainee/support";

/**
 * An organisation's own stations, sat alone.
 *
 * The retiring arm had three screens for this — self practice inside a
 * trainee's workspace, a direct-practice home and its station list for a
 * partner's account — with three API modules behind them and their own mock
 * runner, timers and feedback tabs. They differ only in whose library is
 * listed, which is the organisation's in every case, so this is one screen.
 *
 * Everything between "start" and "ended" is `capabilities/attempt-runner`: the
 * reading clock, the microphone check, the room, the patient tile, the
 * wind-down cue and the hang-up. All this adds is the one call that differs —
 * `POST /attempts` with the station's published version — which is why it is a
 * hundred lines rather than the eighteen files it replaces.
 *
 * The platform's own library is a different list and already has a screen: the
 * stations capability, mounted on this arm.
 */
export function SelfPractice({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const [chosen, setChosen] = useState<OrgStation | null>(null);
  const state = useAsync((signal) => listOrgStations(orgSlug, signal), [orgSlug]);
  const exams = useAsync(async (signal) => (await listExams(signal)).items, []);

  if (chosen) {
    return (
      <Consultation
        station={chosen}
        exam={exams.data?.find((item) => item.code === chosen.exam_code) ?? null}
        onLeave={() => setChosen(null)}
      />
    );
  }

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-b2b-border pb-4">
        <div className="min-w-0">
          <p className={b2bTokens.b2bEyebrow}>Self practice</p>
          <h1 className={`mt-1 ${b2bTokens.b2bPageTitle}`}>Your organisation&apos;s stations</h1>
          <p className={`mt-1 ${b2bTokens.b2bHeroSubtitle} ${b2bTokens.b2bProseMeasure}`}>
            Sit one on your own, with the simulated patient and no supervisor. Nothing here is
            marked as an examination.
          </p>
        </div>
        <ButtonLink themeType="b2b" variant="secondary" size="sm" href={hrefFor("/stations")}>
          Platform library
        </ButtonLink>
      </header>

      <AsyncBoundary state={state} isEmpty={(stations) => practisable(stations).length === 0}
        empty={{
          title: "No published stations yet",
          description:
            "Your organisation has not published any station cases. Until it does, the platform library is still open to you.",
        }}
      >
        {(stations) => <StationList stations={stations} onChoose={setChosen} />}
      </AsyncBoundary>
    </div>
  );
}

function StationList({
  stations,
  onChoose,
}: {
  stations: readonly OrgStation[];
  onChoose: (station: OrgStation) => void;
}) {
  const rows = useMemo(() => practisable(stations), [stations]);
  const withheld = stations.length - rows.length;

  return (
    <section className="space-y-2">
      <p className={b2bTokens.b2bEyebrow}>
        {rows.length} station{rows.length === 1 ? "" : "s"} you can sit
      </p>
      <div className={b2bTokens.b2bGroupedShell}>
        {rows.map((station) => (
          <button
            key={station.id}
            type="button"
            onClick={() => onChoose(station)}
            className={`${b2bTokens.b2bGroupedRow} w-full text-left`}
          >
            <span className={`${b2bTokens.b2bIconChipBase} ${b2bTokens.b2bChipHueClasses.amber}`}>
              <HiOutlineSparkles className="h-5 w-5" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className={b2bTokens.b2bGroupedRowTitle}>{station.title}</p>
              <p className={b2bTokens.b2bGroupedRowSubtitle}>
                {station.exam_code.toUpperCase()} · version {station.version}
              </p>
            </div>
            <HiChevronRight className="h-5 w-5 shrink-0 text-b2b-inactive" aria-hidden />
          </button>
        ))}
      </div>
      {withheld > 0 ? (
        <p className="text-osce-caption text-b2b-mid">
          {withheld} more {withheld === 1 ? "is a draft" : "are drafts"} and cannot be sat until
          published.
        </p>
      ) : null}
    </section>
  );
}

/**
 * One station, run.
 *
 * `self_practice` rather than `practice` because the backend's `attempts.Kind`
 * distinguishes them: a practice attempt is a consumer's own, and this one is
 * sat inside an organisation and carries its `org_id`. Which of the two a row
 * is decides whose station library it was allowed to draw on, so the kind is
 * not cosmetic.
 */
function Consultation({
  station,
  exam,
  onLeave,
}: {
  station: OrgStation;
  exam: Exam | null;
  onLeave: () => void;
}) {
  const { hrefFor } = useSurface();
  const [finished, setFinished] = useState<string | null>(null);

  // Thrown, not caught: `useAttemptSession` owns the failure and renders it
  // beside the retry, which is the only place a candidate can act on it.
  const start = useCallback(async () => {
    const attempt = await createAttempt({
      examCode: station.exam_code,
      kind: "self_practice",
      stationVersionId: station.current_version_id,
    });
    return { id: attempt.id };
  }, [station]);

  if (finished) {
    return (
      <div className="flex w-full min-w-0 flex-col gap-4">
        <Alert tone="success" title="Consultation finished">
          Your feedback is being marked. It appears on the station record as soon as it is ready.
        </Alert>
        <div className="flex flex-wrap gap-2">
          <ButtonLink themeType="b2b" variant="commit" href={hrefFor(`/attempts/${finished}`)}>
            Read your feedback
          </ButtonLink>
          <button type="button" className={b2bTokens.b2bGhostButton} onClick={onLeave}>
            Practise another station
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-full min-w-0 flex-col gap-4">
      <button type="button" onClick={onLeave} className={`self-start ${b2bTokens.b2bLinkMuted}`}>
        Leave and go back to the list
      </button>
      <AttemptRunner
        start={start}
        onEnded={setFinished}
        stationTitle={station.title}
        brief={readingBrief(station)}
        readingSeconds={exam?.default_reading_seconds ?? 0}
        simulationSeconds={exam?.default_simulation_seconds ?? 600}
      />
    </div>
  );
}
