"use client";

import Link from "next/link";
import { LuCircleCheck, LuCircleDashed } from "react-icons/lu";
import { AsyncBoundary, Badge, ButtonLink, Card, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readOrgDashboard, type OrgDashboard as OrgDashboardData } from "@/domains/assess/api";

/** The institution's home screen: what exists, what is next, and what is missing. */
export function OrgDashboard({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => readOrgDashboard(orgSlug, signal), [orgSlug]);
  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>{(data) => <Body data={data} />}</AsyncBoundary>
    </div>
  );
}

function Body({ data }: { data: OrgDashboardData }) {
  const { hrefFor } = useSurface();
  const counts = data.counts;

  return (
    <>
      <PageHeader
        title={data.name}
        description="Your programmes, people and examinations."
        actions={
          data.setup.ready_to_run ? (
            <ButtonLink href={hrefFor("/sittings/new")}>Schedule a sitting</ButtonLink>
          ) : null
        }
      />

      {!data.setup.ready_to_run && <SetupChecklist setup={data.setup} />}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Stat label="Trainees" value={counts.trainees} href={hrefFor("/trainees")} />
        <Stat label="Staff" value={counts.staff} href={hrefFor("/team")} />
        <Stat label="Stations" value={counts.stations} href={hrefFor("/stations")} />
        <Stat label="Sittings" value={counts.sittings} href={hrefFor("/sittings")} />
        <Stat label="Templates" value={counts.published_feedback_templates} />
      </section>

      <Card title="Recent sittings">
        {(data.recent_sittings ?? []).length === 0 ? (
          <p className="text-sm text-ink-muted">Nothing scheduled yet.</p>
        ) : (
          <ul className="divide-y divide-border">
            {(data.recent_sittings ?? []).map((sitting) => (
              <li key={sitting.id}>
                <Link
                  href={hrefFor(`/sittings/${sitting.id}`)}
                  className="flex flex-wrap items-center justify-between gap-3 py-3 hover:underline"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-ink">
                      {sitting.name}
                    </span>
                    {sitting.scheduled_for && (
                      <span className="text-xs text-ink-subtle">
                        {new Date(sitting.scheduled_for).toLocaleString()}
                      </span>
                    )}
                  </span>
                  <span className="flex items-center gap-2">
                    <Badge tone="neutral">{sitting.mode}</Badge>
                    <Badge tone={sitting.status === "live" ? "success" : "neutral"}>
                      {sitting.status}
                    </Badge>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}

function Stat({ label, value, href }: { label: string; value: number; href?: string }) {
  const body = (
    <Card className={href ? "transition-colors hover:border-border-strong" : undefined}>
      <p className="text-xs uppercase tracking-wide text-ink-subtle">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
    </Card>
  );
  return href ? <Link href={href}>{body}</Link> : body;
}

/**
 * The one next step, rather than five cards competing to be it.
 *
 * `ready_to_run` is the backend's judgement, not a count assembled here, so the
 * screen cannot disagree with what the API will accept.
 */
function SetupChecklist({ setup }: { setup: OrgDashboardData["setup"] }) {
  const steps = [
    { done: setup.team_invited, label: "Invite your team" },
    { done: setup.trainees_added, label: "Add your trainees" },
    { done: setup.stations_authored, label: "Author or adopt stations" },
    { done: setup.feedback_template_published, label: "Publish a feedback template" },
  ];

  return (
    <Card title="Finish setting up" description="A sitting can be scheduled once these are done.">
      <ol className="flex flex-col gap-2">
        {steps.map((step) => (
          <li key={step.label} className="flex items-center gap-2 text-sm">
            {step.done ? (
              <LuCircleCheck className="h-4 w-4 text-success" aria-hidden />
            ) : (
              <LuCircleDashed className="h-4 w-4 text-ink-subtle" aria-hidden />
            )}
            <span className={step.done ? "text-ink-muted line-through" : "text-ink"}>
              {step.label}
            </span>
          </li>
        ))}
      </ol>
    </Card>
  );
}
