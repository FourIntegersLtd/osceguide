"use client";

import Link from "next/link";
import { HiChevronRight, HiCheckCircle, HiOutlineCircleStack } from "react-icons/hi2";
import { AsyncBoundary, ButtonLink, b2bTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { readOrgDashboard, type OrgDashboard as Data } from "@/domains/assess/dashboard/api";
import { LiveNow } from "@/domains/assess/dashboard/LiveNow";
import { SupervisorCircuits } from "@/domains/assess/dashboard/SupervisorCircuits";
import {
  dashboardLead,
  nextStep,
  setupProgress,
  setupSteps,
} from "@/domains/assess/dashboard/support";

/**
 * The institution's home screen.
 *
 * Two screens in the retiring client, chosen by reading a role string: an
 * administrator's and a supervisor's. It is one screen here, and what is on it
 * comes from what the backend says this person may do — a supervisor who is
 * also an admin sees both halves rather than whichever the role check picked.
 */
export function OrgDashboard({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => readOrgDashboard(orgSlug, signal), [orgSlug]);
  const { session } = useSession();
  const admin = can(session, "manage_team");
  const runs = can(session, "run_circuits");

  return (
    <div className="flex w-full min-w-0 flex-col gap-5">
      <AsyncBoundary state={state}>
        {(data) => (
          <Body data={data} orgSlug={orgSlug} admin={admin} runs={runs} />
        )}
      </AsyncBoundary>
    </div>
  );
}

function Body({
  data,
  orgSlug,
  admin,
  runs,
}: {
  data: Data;
  orgSlug: string;
  admin: boolean;
  runs: boolean;
}) {
  const { hrefFor } = useSurface();
  const step = nextStep(data.setup);

  return (
    <>
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-b2b-border pb-4">
        <div className="min-w-0">
          <p className={b2bTokens.b2bEyebrow}>{data.slug}</p>
          <h1 className={`mt-1 ${b2bTokens.b2bPageTitle}`}>{data.name}</h1>
          <p className="mt-1 text-osce-caption text-b2b-mid">{dashboardLead(data)}</p>
        </div>
        {data.setup.ready_to_run ? (
          <ButtonLink href={hrefFor("/sittings/new")} themeType="b2b" variant="commit">
            Schedule a sitting
          </ButtonLink>
        ) : step ? (
          <ButtonLink href={hrefFor(step.path)} themeType="b2b" variant="commit">
            Continue setting up
          </ButtonLink>
        ) : null}
      </header>

      {/* What is happening now comes before what exists: on an examination
          morning it is the only thing anybody wants. */}
      {runs ? <LiveNow orgSlug={orgSlug} /> : null}

      {!data.setup.ready_to_run ? <Setup data={data} /> : null}

      {/* A supervisor needs the empty state — it says why their screen is
          otherwise blank. An administrator who happens to supervise nothing
          does not, and a permanent "nothing is assigned to you" is noise. */}
      {runs ? <SupervisorCircuits orgSlug={orgSlug} sayWhenEmpty={!admin} /> : null}

      {admin ? <Counts data={data} /> : null}

      <section className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <h2 className={b2bTokens.b2bEyebrow}>Recent sittings</h2>
          <Link href={hrefFor("/sittings")} className={b2bTokens.b2bLink}>
            All sittings
          </Link>
        </div>
        {(data.recent_sittings ?? []).length === 0 ? (
          <p className="text-osce-body text-b2b-mid">Nothing scheduled yet.</p>
        ) : (
          <div className={b2bTokens.b2bGroupedShell}>
            {(data.recent_sittings ?? []).map((sitting) => (
              <Link
                key={sitting.id}
                href={hrefFor(`/sittings/${sitting.id}`)}
                className={`${b2bTokens.b2bGroupedRow} hover:bg-b2b-cream`}
              >
                <div className="min-w-0 flex-1">
                  <p className={b2bTokens.b2bGroupedRowTitle}>{sitting.name}</p>
                  <p className={b2bTokens.b2bGroupedRowSubtitle}>
                    {sitting.mode} · {sitting.status.replace(/_/g, " ")}
                    {sitting.scheduled_for
                      ? ` · ${new Date(sitting.scheduled_for).toLocaleString()}`
                      : ""}
                  </p>
                </div>
                <HiChevronRight className="h-5 w-5 shrink-0 text-b2b-inactive" aria-hidden />
              </Link>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

/**
 * The one next step, with the rest behind it.
 *
 * `ready_to_run` is the backend's judgement. The old checklist counted five
 * listings in the browser, so a failed fetch told somebody to do work they had
 * already done.
 */
function Setup({ data }: { data: Data }) {
  const { hrefFor } = useSurface();
  const steps = setupSteps(data.setup);
  const progress = setupProgress(data.setup);

  return (
    <section className="space-y-3 rounded-lg border border-b2b-border bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className={b2bTokens.b2bSectionTitle}>Before your first examination</h2>
        <span className="text-osce-caption tabular-nums text-b2b-mid">
          {progress.done}/{progress.total} done
        </span>
      </div>

      <div className="h-1 overflow-hidden rounded-full bg-b2b-border/40">
        <div
          className="h-full rounded-full bg-b2b-accent transition-[width] duration-500 ease-out"
          style={{ width: `${progress.percent}%` }}
        />
      </div>

      <ol className="divide-y divide-b2b-border">
        {steps.map((step) => (
          <li key={step.key}>
            <Link
              href={hrefFor(step.path)}
              className="flex items-start gap-3 py-3 hover:bg-b2b-cream/60"
            >
              {step.done ? (
                <HiCheckCircle className="mt-0.5 h-5 w-5 shrink-0 text-b2b-success-icon" aria-hidden />
              ) : (
                <HiOutlineCircleStack className="mt-0.5 h-5 w-5 shrink-0 text-b2b-icon" aria-hidden />
              )}
              <span className="min-w-0 flex-1">
                <span
                  className={`block text-osce-body font-medium ${
                    step.done ? "text-b2b-mid line-through" : "text-b2b-headline"
                  }`}
                >
                  {step.label}
                </span>
                <span className="mt-0.5 block text-osce-caption leading-snug text-b2b-mid">
                  {step.hint}
                </span>
              </span>
              {!step.done ? (
                <HiChevronRight className="mt-1 h-5 w-5 shrink-0 text-b2b-inactive" aria-hidden />
              ) : null}
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Counts({ data }: { data: Data }) {
  const { hrefFor } = useSurface();
  const counts = data.counts;
  const tiles = [
    { label: "Trainees", value: counts.trainees, path: "/trainees" },
    { label: "Staff", value: counts.staff, path: "/team" },
    // The backend counts this organisation's own stations, not the
    // platform catalogue it may also run, so it is named that way.
    { label: "Your stations", value: counts.stations, path: "/authoring" },
    { label: "Sittings", value: counts.sittings, path: "/sittings" },
    { label: "Templates", value: counts.published_feedback_templates, path: null },
  ];

  return (
    <section className="space-y-2">
      <h2 className={b2bTokens.b2bEyebrow}>At a glance</h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {tiles.map((tile) => {
          const body = (
            <div className="rounded-lg border border-b2b-border bg-white px-4 py-3">
              <p className="text-osce-caption uppercase tracking-wide text-b2b-mid">{tile.label}</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-b2b-headline">
                {tile.value}
              </p>
            </div>
          );
          return tile.path ? (
            <Link key={tile.label} href={hrefFor(tile.path)} className="hover:opacity-90">
              {body}
            </Link>
          ) : (
            <div key={tile.label}>{body}</div>
          );
        })}
      </div>
    </section>
  );
}
