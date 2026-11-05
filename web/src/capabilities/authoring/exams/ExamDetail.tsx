"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Alert, AsyncBoundary, B2CPageHeader, Badge, Button, ButtonLink, Panel, Switch, TextLink } from "@/foundation/ui";
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
import { examSettingsPath, examsListPath } from "@/capabilities/authoring/exams/paths";
import { shortDay, schemeLine } from "@/capabilities/authoring/exams/schemeLine";
import { timingsLine, toMinutes } from "@/capabilities/authoring/exams/newExam";
import { loadExam } from "@/capabilities/authoring/exams/useExam";
import { availabilityPlan, examChip, toggleHelp } from "@/capabilities/authoring/sections/examSteps";
import { stationNewForExamPath, stationsForExamPath, stationsListPath } from "@/capabilities/authoring/stations/paths";
import { examResumePath, rubricEditPath, rubricsListPath, stationTemplatesListPath } from "@/capabilities/authoring/templates/paths";

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
        listStations(scope, { exam_code: exam.code, limit: COUNT_LIMIT }, signal),
        listRubrics(scope, {}, signal),
        listStationTemplatesPage(scope, { exam_code: exam.code, limit: COUNT_LIMIT }, signal),
        programme ? countProgrammeSittings(scope, programme.id, signal) : Promise.resolve(null),
      ]);
      const scheme = rubrics.items
        .flatMap((rubric) => (rubric.versions ?? []).map((v) => ({ rubric, v })))
        .find(({ v }) => v.id === exam.rubric_version_id);
      return {
        exam,
        programme,
        stations: stations.items,
        templates: templates.items,
        sittings: sittings?.items ?? [],
        scheme: scheme ? { rubricId: scheme.rubric.id, title: scheme.rubric.title, version: scheme.v } : null,
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
          <Alert tone="danger">This exam could not be found. It may have been deleted.</Alert>
        ) : (
          <ExamDetailBody {...data} reload={view.reload} />
        )
      }
    </AsyncBoundary>
  );
}

function ExamDetailBody({ exam, programme, stations, templates, sittings, scheme, reload }: View & { reload: () => void }) {
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
      let state: { exam: Exam; programme: Programme | null } = { exam, programme };
      for (const step of availabilityPlan(programme, next)) state = await applyStep(scope, step, state);
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        eyebrow={
          <span className="inline-flex items-center gap-2">
            {exam.code}
            <Badge tone={chip === "Ready to schedule" ? "success" : "warning"} size="sm" dot>
              {chip}
            </Badge>
          </span>
        }
        title={exam.name}
        subtitle={[
          plural(published, "published station", "published stations"),
          scheme ? `Marking scheme v${scheme.version.version}` : "No marking scheme",
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

      <Panel className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-osce-body font-semibold text-ink">Available for scheduling</p>
          <p className="text-osce-caption text-ink-muted">
            {exam.status === "published" ? toggleHelp(on) : "Finish setting the exam up and publish it, then switch this on."}
          </p>
          {exam.status === "draft" && canAuthor ? (
            <TextLink href={examResumePath(hrefFor, exam.id)} variant="muted" className="text-osce-meta">
              Continue setup
            </TextLink>
          ) : null}
        </div>
        <Switch checked={on} onChange={toggle} label="Available for scheduling" disabled={!mayToggle || action.busy !== null} />
      </Panel>

      <Panel className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-osce-body font-semibold text-ink">Stations</h2>
          {canAuthor ? (
            <TextLink href={stationNewForExamPath(hrefFor, exam.code)} variant="muted" className="text-osce-meta">
              Add station
            </TextLink>
          ) : null}
        </div>
        {stations.length === 0 ? (
          <p className="text-osce-body text-ink-muted">No stations yet. Create one with Add station.</p>
        ) : (
          <ul className="divide-y divide-border">
            {stations.slice(0, 3).map((station) => (
              <li key={station.id}>
                <Link
                  href={`${stationsListPath(hrefFor)}?station=${encodeURIComponent(station.id)}`}
                  className="flex items-center justify-between gap-3 py-2 hover:bg-canvas"
                >
                  <span className="min-w-0 truncate text-osce-body text-ink">{station.title}</span>
                  <Badge tone={station.status === "published" ? "success" : "warning"} size="sm">
                    {stationState(station.status, station.version)}
                  </Badge>
                </Link>
              </li>
            ))}
          </ul>
        )}
        <TextLink href={stationsForExamPath(hrefFor, exam.code)} variant="muted" className="text-osce-meta">
          {`See all ${stations.length >= COUNT_LIMIT ? `${COUNT_LIMIT}+` : stations.length} stations`}
        </TextLink>
      </Panel>

      <Panel className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-osce-body font-semibold text-ink">Sittings</h2>
          <TextLink href={hrefFor("/sittings")} variant="muted" className="text-osce-meta">
            All sittings
          </TextLink>
        </div>
        {sittings.length === 0 ? (
          <p className="text-osce-body text-ink-muted">No sittings scheduled for this exam yet.</p>
        ) : (
          <ul className="divide-y divide-border">
            {sittings.slice(0, 2).map((sitting) => (
              <li key={sitting.id}>
                <Link
                  href={hrefFor(`/sittings/${encodeURIComponent(sitting.id)}`)}
                  className="flex items-center justify-between gap-3 py-2 hover:bg-canvas"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-osce-body text-ink">{sitting.name}</span>
                    <span className="block text-osce-caption text-ink-muted">
                      {`${sitting.scheduled_for ? `${shortDay(sitting.scheduled_for)} · ` : ""}${sentence(sitting.sitting_type)}`}
                    </span>
                  </span>
                  <Badge tone="neutral" size="sm">
                    {sentence(sitting.status)}
                  </Badge>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel className="flex flex-col gap-2">
        <h2 className="text-osce-body font-semibold text-ink">Marking scheme</h2>
        <p className="text-osce-body text-ink">{scheme ? scheme.title : "None chosen yet."}</p>
        {scheme ? <p className="text-osce-caption text-ink-muted">{schemeLine(scheme.version)}</p> : null}
        <div className="flex flex-wrap gap-3">
          <TextLink
            href={scheme ? rubricEditPath(hrefFor, scheme.rubricId, scheme.version.version, exam.id) : rubricsListPath(hrefFor)}
            variant="muted"
            className="text-osce-meta"
          >
            Open scheme
          </TextLink>
          {canAuthor ? (
            <TextLink href={examSettingsPath(hrefFor, exam.id)} variant="muted" className="text-osce-meta">
              Change scheme
            </TextLink>
          ) : null}
        </div>
      </Panel>

      <Panel className="flex flex-col gap-2">
        <h2 className="text-osce-body font-semibold text-ink">Station layouts (optional)</h2>
        {layouts.length > 0 ? <p className="text-osce-body text-ink-muted">{layouts.join(" · ")}</p> : null}
        <TextLink href={stationTemplatesListPath(hrefFor)} variant="muted" className="text-osce-meta">
          Manage layouts
        </TextLink>
      </Panel>

      <Panel className="flex flex-col gap-2">
        <h2 className="text-osce-body font-semibold text-ink">Settings</h2>
        <p className="text-osce-body text-ink-muted">
          {`${timingsLine({ reading: String(toMinutes(exam.default_reading_seconds)), simulation: String(toMinutes(exam.default_simulation_seconds)) })} · Patient voice and feedback style`}
        </p>
        <TextLink href={examSettingsPath(hrefFor, exam.id)} variant="muted" className="text-osce-meta">
          Edit settings
        </TextLink>
      </Panel>

      {canAuthor && !locked ? (
        <Panel className="flex flex-col gap-3">
          <h2 className="text-osce-body font-semibold text-ink">Retire or delete</h2>
          <div className="flex flex-wrap gap-3">
            {exam.status === "published" ? (
              <Button variant="secondary" size="sm" disabled={action.busy !== null} onClick={() => setRetiring(exam)}>
                Retire exam
              </Button>
            ) : null}
            <Button variant="secondary" size="sm" disabled={action.busy !== null || inUse} onClick={() => setDeleting(exam)}>
              Delete exam
            </Button>
          </div>
          {inUse ? (
            <p className="text-osce-caption text-ink-muted">
              Can&apos;t delete: this exam has sittings and recordings. Retire it instead, and its records stay.
            </p>
          ) : null}
        </Panel>
      ) : null}

      <ExamConfirm kind="retire" scope={scope} exam={retiring} action={action} onCancel={() => setRetiring(null)} />
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
