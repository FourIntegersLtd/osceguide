"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Alert, AsyncBoundary, B2CPageHeader, Badge, Button, Panel } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  addProgramme,
  countProgrammeSittings,
  listExams,
  listProgrammes,
  listRubrics,
  listStations,
  updateProgramme,
  type Exam,
  type Programme,
} from "@/capabilities/authoring/api";
import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { DeleteExamConfirm, RetireExamConfirm } from "@/capabilities/authoring/exams/ExamConfirms";
import { examSettingsPath, examsListPath } from "@/capabilities/authoring/exams/paths";
import { availabilityPlan, examChip, toggleHelp } from "@/capabilities/authoring/sections/examSteps";
import { stationNewPath, stationsListPath } from "@/capabilities/authoring/stations/paths";
import { rubricsListPath } from "@/capabilities/authoring/templates/paths";

/** How many of an exam's stations and sittings one read looks at; a count at the limit reads "100+". */
const COUNT_LIMIT = 100;

function useExamView(examId: string) {
  const scope = useAuthoringScope();
  return useAsync(
    async (signal) => {
      const exams = await listExams(scope, { status: "all" }, signal);
      const exam = exams.items.find((item) => item.id === examId) ?? null;
      if (!exam) return null;
      const [programmes, stations, rubrics] = await Promise.all([
        listProgrammes(scope, signal),
        listStations(scope, { exam_code: exam.code, limit: COUNT_LIMIT }, signal),
        listRubrics(scope, {}, signal),
      ]);
      const programme = programmes.items.find((item) => item.exam_code === exam.code) ?? null;
      const sittings = programme ? (await countProgrammeSittings(scope, programme.id, signal)).items.length : 0;
      const scheme = rubrics.items
        .flatMap((rubric) => (rubric.versions ?? []).map((v) => ({ title: rubric.title, version: v.version, id: v.id })))
        .find((v) => v.id === exam.rubric_version_id);
      return { exam, programme, stations: stations.items, sittings, scheme: scheme ?? null };
    },
    [scope.base, examId],
  );
}

function plural(n: number, one: string, many: string): string {
  const shown = n >= COUNT_LIMIT ? `${COUNT_LIMIT}+` : String(n);
  return `${shown} ${n === 1 ? one : many}`;
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

function ExamDetailBody({
  exam,
  programme,
  stations,
  sittings,
  scheme,
  reload,
}: {
  exam: Exam;
  programme: Programme | null;
  stations: { id: string; title: string; status: string }[];
  sittings: number;
  scheme: { title: string; version: number } | null;
  reload: () => void;
}) {
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
  const inUse = stations.length > 0 || sittings > 0;
  const mayToggle = canAuthor && exam.status === "published" && !locked;

  function toggle(next: boolean) {
    void action.run("available", async () => {
      let current: Programme | null = programme;
      for (const step of availabilityPlan(programme, next)) {
        if (step === "add") current = await addProgramme(scope, exam.code);
        else if (current) current = await updateProgramme(scope, current.id, step === "activate" ? "active" : "retired");
      }
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
          scheme ? `Marking scheme v${scheme.version}` : "No marking scheme",
          plural(sittings, "sitting", "sittings"),
        ].join(" · ")}
        back={{ href: examsListPath(hrefFor), label: "Exams" }}
        action={
          programme?.status === "active" ? (
            <Link
              href={hrefFor("/sittings/new")}
              className="inline-flex min-h-11 items-center rounded-osce-md bg-osce-accent px-4 text-osce-body font-semibold text-white hover:bg-osce-accent-hover"
            >
              Schedule a sitting
            </Link>
          ) : null
        }
      />

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <Panel className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-osce-body font-semibold text-ink">Available for scheduling</p>
          <p className="text-osce-caption text-ink-muted">
            {exam.status === "published" ? toggleHelp(on) : "Publish the exam first, then switch this on."}
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={on}
          aria-label="Available for scheduling"
          disabled={!mayToggle || action.busy !== null}
          onClick={() => toggle(!on)}
          className={`relative h-6 w-11 shrink-0 rounded-full border border-transparent transition-colors disabled:opacity-50 ${
            on ? "bg-osce-accent" : "bg-surface-raised border-border"
          }`}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${on ? "left-[22px]" : "left-0.5"}`}
          />
        </button>
      </Panel>

      <Panel className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-osce-body font-semibold text-ink">Stations</h2>
          {canAuthor ? (
            <Link href={stationNewPath(hrefFor)} className="text-osce-meta font-medium text-osce-accent hover:underline">
              Add station
            </Link>
          ) : null}
        </div>
        {stations.length === 0 ? (
          <p className="text-osce-body text-ink-muted">No stations yet. Create one with Add station.</p>
        ) : (
          <ul className="divide-y divide-border">
            {stations.slice(0, 3).map((station) => (
              <li key={station.id} className="flex items-center justify-between gap-3 py-2">
                <span className="min-w-0 truncate text-osce-body text-ink">{station.title}</span>
                <Badge tone={station.status === "published" ? "success" : "warning"} size="sm">
                  {station.status === "published" ? "Published" : "Draft"}
                </Badge>
              </li>
            ))}
          </ul>
        )}
        <Link href={stationsListPath(hrefFor)} className="text-osce-meta font-medium text-osce-accent hover:underline">
          {`See all ${stations.length >= COUNT_LIMIT ? `${COUNT_LIMIT}+` : stations.length} stations`}
        </Link>
      </Panel>

      <Panel className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-osce-body font-semibold text-ink">Sittings</h2>
          <Link href={hrefFor("/sittings")} className="text-osce-meta font-medium text-osce-accent hover:underline">
            All sittings
          </Link>
        </div>
        <p className="text-osce-body text-ink-muted">
          {sittings === 0 ? "No sittings scheduled for this exam yet." : plural(sittings, "sitting", "sittings")}
        </p>
      </Panel>

      <Panel className="flex flex-col gap-2">
        <h2 className="text-osce-body font-semibold text-ink">Marking scheme</h2>
        <p className="text-osce-body text-ink">{scheme ? scheme.title : "None chosen yet."}</p>
        {scheme ? <p className="text-osce-caption text-ink-muted">Version {scheme.version}</p> : null}
        <div className="flex flex-wrap gap-3">
          <Link href={rubricsListPath(hrefFor)} className="text-osce-meta font-medium text-osce-accent hover:underline">
            Open scheme
          </Link>
          {canAuthor ? (
            <Link href={examSettingsPath(hrefFor, exam.id)} className="text-osce-meta font-medium text-osce-accent hover:underline">
              Change scheme
            </Link>
          ) : null}
        </div>
      </Panel>

      <Panel className="flex flex-col gap-2">
        <h2 className="text-osce-body font-semibold text-ink">Station layouts (optional)</h2>
        <Link
          href={`${hrefFor("/authoring")}/station-templates`}
          className="text-osce-meta font-medium text-osce-accent hover:underline"
        >
          Manage layouts
        </Link>
      </Panel>

      <Panel className="flex flex-col gap-2">
        <h2 className="text-osce-body font-semibold text-ink">Settings</h2>
        <p className="text-osce-body text-ink-muted">
          {`${Math.round(exam.default_reading_seconds / 60)} min reading · ${Math.round(exam.default_simulation_seconds / 60)} min consultation · Patient voice and feedback style`}
        </p>
        <Link href={examSettingsPath(hrefFor, exam.id)} className="text-osce-meta font-medium text-osce-accent hover:underline">
          Edit settings
        </Link>
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

      <RetireExamConfirm scope={scope} exam={retiring} action={action} onCancel={() => setRetiring(null)} />
      <DeleteExamConfirm
        scope={scope}
        exam={deleting}
        action={action}
        onCancel={() => setDeleting(null)}
        onDone={() => router.push(examsListPath(hrefFor))}
      />
    </div>
  );
}
