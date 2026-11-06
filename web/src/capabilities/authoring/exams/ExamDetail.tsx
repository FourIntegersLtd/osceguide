"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Alert,
  AsyncBoundary,
  B2CPageHeader,
  ButtonLink,
} from "@/foundation/ui";
import {
  boardBtn,
  boardCard,
  boardCardClipped,
  boardCols,
  boardColsMain,
  boardColsRail,
  boardKnob,
  boardRailCard,
  boardRow,
  boardToggle,
  type BoardChipTone,
} from "@/foundation/ui/boardKit";
import { BoardChip, boardMeta } from "@/capabilities/authoring/parts/boardUi";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  countProgrammeSittings,
  listRubrics,
  listStations,
  listStationTemplatesPage,
  type Exam,
  type Programme,
} from "@/capabilities/authoring/api";
import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { ExamConfirm } from "@/capabilities/authoring/exams/ExamConfirms";
import { applyStep } from "@/capabilities/authoring/exams/offer";
import {
  examSettingsPath,
  examsListPath,
} from "@/capabilities/authoring/exams/paths";
import {
  shortDay,
  schemeLine,
} from "@/capabilities/authoring/exams/schemeLine";
import { timingsLine, toMinutes } from "@/capabilities/authoring/exams/newExam";
import { layoutName } from "@/capabilities/authoring/exams/layoutName";
import { loadExam } from "@/capabilities/authoring/exams/useExam";
import {
  availabilityPlan,
  examChip,
  toggleHelp,
} from "@/capabilities/authoring/sections/examSteps";
import {
  stationNewForExamPath,
  stationsForExamPath,
  stationsListPath,
} from "@/capabilities/authoring/stations/paths";
import {
  examResumePath,
  rubricEditPath,
  rubricsListPath,
  stationTemplatesListPath,
} from "@/capabilities/authoring/templates/paths";

/** How many of an exam's stations and sittings one read looks at; a count at the limit reads "100+". */
const COUNT_LIMIT = 100;

function useExamView(examId: string) {
  const scope = useAuthoringScope();
  return useAsync(
    async (signal) => {
      const found = await loadExam(scope, examId, signal);
      if (!found) return null;
      const { exam, programme } = found;
      const [stations, rubrics, templates, sittings] = await Promise.all([
        listStations(
          scope,
          { exam_code: exam.code, limit: COUNT_LIMIT },
          signal,
        ),
        listRubrics(scope, {}, signal),
        listStationTemplatesPage(
          scope,
          { exam_code: exam.code, limit: COUNT_LIMIT },
          signal,
        ),
        programme
          ? countProgrammeSittings(scope, programme.id, signal)
          : Promise.resolve(null),
      ]);
      const scheme = rubrics.items
        .flatMap((rubric) =>
          (rubric.versions ?? []).map((v) => ({ rubric, v })),
        )
        .find(({ v }) => v.id === exam.rubric_version_id);
      return {
        exam,
        programme,
        stations: stations.items,
        templates: templates.items,
        sittings: sittings?.items ?? [],
        scheme: scheme
          ? {
              rubricId: scheme.rubric.id,
              title: scheme.rubric.title,
              version: scheme.v,
            }
          : null,
      };
    },
    [scope.base, examId],
  );
}

type View = NonNullable<ReturnType<typeof useExamView>["data"]>;

function plural(n: number, one: string, many: string): string {
  const shown = n >= COUNT_LIMIT ? `${COUNT_LIMIT}+` : String(n);
  return `${shown} ${n === 1 ? one : many}`;
}

/** "Published v2" / "Draft": a station's state as the board words it. */
function stationState(status: string, version: number): string {
  return status === "published" ? `Published v${version}` : "Draft";
}

/** The board's chip colour for a sitting's state. */
function sittingTone(status: string): BoardChipTone {
  if (status === "scheduled") return "info";
  if (status === "running" || status === "live") return "warn";
  return "neutral";
}

const cardHead = "flex flex-wrap items-center justify-between gap-3 px-5 py-4";
const cardTitle = "text-assess-hero font-semibold leading-snug text-ink";
const railEyebrow = "text-assess-eyebrow font-normal uppercase text-ink-subtle";

function sentence(value: string): string {
  const spaced = value.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** One exam: whether it is offered for scheduling, its stations, sittings, marking scheme and settings. */
export function ExamDetail({ examId }: { examId: string }) {
  const view = useExamView(examId);
  return (
    <AsyncBoundary state={view}>
      {(data) =>
        data === null ? (
          <Alert tone="danger">
            This exam could not be found. It may have been deleted.
          </Alert>
        ) : (
          <ExamDetailBody {...data} reload={view.reload} />
        )
      }
    </AsyncBoundary>
  );
}

function ExamDetailBody({
  exam,
  programme,
  stations,
  templates,
  sittings,
  scheme,
  reload,
}: View & { reload: () => void }) {
  const scope = useAuthoringScope();
  const { hrefFor } = useSurface();
  const router = useRouter();
  const canAuthor = useCanAuthor();
  const action = useAction(reload);
  const [retiring, setRetiring] = useState<Exam | null>(null);
  const [deleting, setDeleting] = useState<Exam | null>(null);

  const on = programme?.status === "active";
  const chip = examChip(exam, programme);
  const published = stations.filter((s) => s.status === "published").length;
  const locked = exam.owner_kind === "platform";
  const inUse = stations.length > 0 || sittings.length > 0;
  // An adopted exam is the platform's, but its programme is this organisation's own: only Retire and Delete are locked.
  const mayToggle = canAuthor && exam.status === "published";
  const layouts = templates.map((template) => template.title);

  function toggle(next: boolean) {
    void action.run("available", async () => {
      let state: { exam: Exam; programme: Programme | null } = {
        exam,
        programme,
      };
      for (const step of availabilityPlan(programme, next))
        state = await applyStep(scope, step, state);
    });
  }

  return (
    <div className="flex max-w-[1080px] flex-col gap-6" data-testid="exam-detail-page">
      <B2CPageHeader
        board="tight"
        className="!mb-0"
        eyebrow={
          <span className="flex items-center gap-2.5 font-sans normal-case tracking-normal">
            <span className="text-assess-eyebrow font-normal uppercase tracking-[0.06em] text-ink-subtle">{exam.code}</span>
            <BoardChip tone={chip === "Ready to schedule" ? "ok" : "warn"}>{chip}</BoardChip>
          </span>
        }
        title={exam.name}
        subtitle={[
          plural(published, "published station", "published stations"),
          scheme
            ? `Marking scheme v${scheme.version.version}`
            : "No marking scheme",
          plural(sittings.length, "sitting", "sittings"),
        ].join(" · ")}
        back={{ href: examsListPath(hrefFor), label: "Exams" }}
        action={
          programme?.status === "active" ? (
            <ButtonLink href={hrefFor("/sittings/new")} variant="primary">
              Schedule a sitting
            </ButtonLink>
          ) : null
        }
      />

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <div className={`${boardCard} flex flex-wrap items-center gap-4 px-5 py-[18px]`}>
        <div className="min-w-[280px] flex-1">
          <p className="text-assess-desc font-medium !leading-[normal] text-ink">Available for scheduling</p>
          <p className={boardMeta}>
            {exam.status === "published"
              ? toggleHelp(on)
              : "Finish setting the exam up and publish it, then switch this on."}
          </p>
          {exam.status === "draft" && canAuthor ? (
            <Link href={examResumePath(hrefFor, exam.id)} className={`${boardMeta} text-osce-accent`}>
              Continue setup
            </Link>
          ) : null}
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={on}
          aria-label="Available for scheduling"
          disabled={!mayToggle || action.busy !== null}
          onClick={() => toggle(!on)}
          className={boardToggle(on)}
        >
          <span className={boardKnob} aria-hidden />
        </button>
      </div>

      <div className={boardCols}>
        <div className={boardColsMain}>
          <div className={boardCardClipped}>
            <div className={cardHead}>
              <h2 className={cardTitle}>Stations</h2>
              {canAuthor ? (
                <Link href={stationNewForExamPath(hrefFor, exam.code)} className={boardBtn()}>
                  Add station
                </Link>
              ) : null}
            </div>
            {stations.length === 0 ? (
              <p className={`${boardRow} ${boardMeta}`}>No stations yet. Create one with Add station.</p>
            ) : (
              stations.slice(0, 3).map((station) => {
                const layout = layoutName(templates, station.template_version_id);
                return (
                  <Link
                    key={station.id}
                    href={`${stationsListPath(hrefFor)}?station=${encodeURIComponent(station.id)}`}
                    className={`${boardRow} hover:bg-osce-canvas`}
                  >
                    <span className="min-w-[220px] flex-1 font-medium">{station.title}</span>
                    {layout ? <span className={boardMeta}>{layout}</span> : null}
                    <BoardChip tone={station.status === "published" ? "ok" : "neutral"}>
                      {stationState(station.status, station.version)}
                    </BoardChip>
                  </Link>
                );
              })
            )}
            <div className={boardRow}>
              <Link href={stationsForExamPath(hrefFor, exam.code)} className="text-osce-accent">
                {`See all ${stations.length >= COUNT_LIMIT ? `${COUNT_LIMIT}+` : stations.length} stations`}
              </Link>
            </div>
          </div>

          <div className={boardCardClipped}>
            <div className={cardHead}>
              <h2 className={cardTitle}>Sittings</h2>
              <Link
                href={
                  programme
                    ? `${hrefFor("/sittings")}?exam=${encodeURIComponent(programme.id)}`
                    : hrefFor("/sittings")
                }
                className="text-assess-label text-osce-accent"
              >
                All sittings
              </Link>
            </div>
            {sittings.length === 0 ? (
              <p className={`${boardRow} ${boardMeta}`}>No sittings scheduled for this exam yet.</p>
            ) : (
              sittings.slice(0, 2).map((sitting) => (
                <Link
                  key={sitting.id}
                  href={hrefFor(`/sittings/${encodeURIComponent(sitting.id)}`)}
                  className={`${boardRow} hover:bg-osce-canvas`}
                >
                  <span className="min-w-[220px] flex-1 truncate font-medium">{sitting.name}</span>
                  <span className={boardMeta}>
                    {`${sitting.scheduled_for ? `${shortDay(sitting.scheduled_for)} · ` : ""}${sentence(sitting.sitting_type)}`}
                  </span>
                  <BoardChip tone={sittingTone(sitting.status)}>{sentence(sitting.status)}</BoardChip>
                </Link>
              ))
            )}
          </div>
        </div>

        <div className={boardColsRail}>
          <div className={boardRailCard}>
            <h2 className={railEyebrow}>Marking scheme</h2>
            <p className="text-assess-desc font-medium !leading-[normal]">{scheme ? scheme.title : "None chosen yet."}</p>
            {scheme ? <p className={boardMeta}>{schemeLine(scheme.version)}</p> : null}
            <div className="flex flex-wrap gap-2.5">
              <Link
                href={
                  scheme
                    ? rubricEditPath(hrefFor, scheme.rubricId, scheme.version.version, exam.id)
                    : `${rubricsListPath(hrefFor)}?exam=${encodeURIComponent(exam.code)}`
                }
                className={boardBtn()}
              >
                Open scheme
              </Link>
              {canAuthor ? (
                <Link href={examSettingsPath(hrefFor, exam.id)} className={boardBtn()}>
                  Change scheme
                </Link>
              ) : null}
            </div>
          </div>

          <div className={boardRailCard}>
            <h2 className={railEyebrow}>Station layouts (optional)</h2>
            {layouts.length > 0 ? <p className={boardMeta}>{layouts.join(" · ")}</p> : null}
            <Link href={stationTemplatesListPath(hrefFor)} className="text-assess-label text-osce-accent">
              Manage layouts
            </Link>
          </div>

          <div className={boardRailCard}>
            <h2 className={railEyebrow}>Settings</h2>
            <p className={boardMeta}>
              {`${timingsLine({ reading: String(toMinutes(exam.default_reading_seconds)), simulation: String(toMinutes(exam.default_simulation_seconds)), breakMin: exam.settings?.default_break_minutes ? String(exam.settings.default_break_minutes) : "" })} · Patient voice and feedback style`}
            </p>
            <Link href={examSettingsPath(hrefFor, exam.id)} className="text-assess-label text-osce-accent">
              Edit settings
            </Link>
          </div>

          {canAuthor && !locked ? (
            <div className={boardRailCard}>
              <h2 className={railEyebrow}>Retire or delete</h2>
              {exam.status === "published" ? (
                <button type="button" className={boardBtn()} disabled={action.busy !== null} onClick={() => setRetiring(exam)}>
                  Retire exam
                </button>
              ) : null}
              <button
                type="button"
                className={boardBtn("danger")}
                disabled={action.busy !== null || inUse}
                onClick={() => setDeleting(exam)}
              >
                Delete exam
              </button>
              {inUse ? (
                <p className={boardMeta}>
                  Can&apos;t delete: this exam has sittings and recordings. Retire it instead, and its records stay.
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      <ExamConfirm
        kind="retire"
        scope={scope}
        exam={retiring}
        action={action}
        onCancel={() => setRetiring(null)}
      />
      <ExamConfirm
        kind="delete"
        scope={scope}
        exam={deleting}
        action={action}
        onCancel={() => setDeleting(null)}
        onDone={() => router.push(examsListPath(hrefFor))}
      />
    </div>
  );
}
