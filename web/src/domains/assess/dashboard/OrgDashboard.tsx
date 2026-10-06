"use client";

import Link from "next/link";
import type { IconType } from "react-icons";
import {
  LuCalendarDays,
  LuCheck,
  LuClipboardList,
  LuFolderKanban,
  LuPlus,
  LuUserCog,
  LuUsers,
} from "react-icons/lu";
import {
  AsyncBoundary,
  B2CGroupedRow,
  B2CGroupedRowLink,
  B2CGroupedSection,
  B2CPageHeader,
  Badge,
  ButtonLink,
  b2bTokens,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { readOrgDashboard, type OrgDashboard as Data } from "@/domains/assess/dashboard/api";
import { LiveNow } from "@/domains/assess/dashboard/LiveNow";
import { SupervisorCircuits } from "@/domains/assess/dashboard/SupervisorCircuits";
import {
  nextStep,
  setupProgress,
  setupSteps,
} from "@/domains/assess/dashboard/support";
import { greetingFor } from "@/domains/assess/trainee/support";

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
    <div className="flex w-full min-w-0 flex-col gap-6">
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
  const { session } = useSession();
  const step = nextStep(data.setup);
  const sittings = data.recent_sittings ?? [];

  return (
    <>
      <B2CPageHeader
        className="!mb-0"
        eyebrow={data.name}
        title={greetingFor(session?.user.name, new Date())}
        action={
          !can(session, "schedule_sittings") ? null : data.setup.ready_to_run ? (
            <ButtonLink href={hrefFor("/sittings/new")} themeType="b2b" variant="commit">
              <LuPlus className="h-4 w-4" aria-hidden />
              Schedule a sitting
            </ButtonLink>
          ) : step ? (
            <ButtonLink href={hrefFor(step.path)} themeType="b2b" variant="commit">
              Continue setting up
            </ButtonLink>
          ) : null
        }
      />

      {!data.setup.ready_to_run ? <Setup data={data} /> : null}

      {/* What is happening now comes before what exists: on an examination
          morning it is the only thing anybody wants. */}
      {runs ? <LiveNow orgSlug={orgSlug} /> : null}

      {admin ? <Counts data={data} /> : null}

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start [&>*]:min-w-0 [&>*]:flex-1">
        {/* A supervisor needs the empty state — it says why their screen is
            otherwise blank. An administrator who happens to supervise nothing
            does not, and a permanent "nothing is assigned to you" is noise. */}
        {runs ? <SupervisorCircuits orgSlug={orgSlug} sayWhenEmpty={!admin} /> : null}

        <B2CGroupedSection
          eyebrow="Recent sittings"
          action={
            <Link href={hrefFor("/sittings")} className={b2bTokens.b2bLink}>
              All sittings
            </Link>
          }
        >
          {sittings.length === 0 ? (
            <B2CGroupedRow title="Nothing scheduled yet." />
          ) : (
            sittings.map((sitting) => (
              <B2CGroupedRowLink
                key={sitting.id}
                href={hrefFor(`/sittings/${sitting.id}`)}
                icon={LuCalendarDays}
                title={sitting.name}
                meta={
                  sitting.scheduled_for
                    ? `${new Date(sitting.scheduled_for).toLocaleString()} · ${sitting.mode}`
                    : sitting.mode
                }
                trailing={
                  <Badge variant="neutral" dot>
                    {sentenceCase(sitting.status)}
                  </Badge>
                }
              />
            ))
          )}
        </B2CGroupedSection>
      </div>
    </>
  );
}

function sentenceCase(status: string): string {
  const words = status.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const STEP_ICONS: Record<string, IconType> = {
  team: LuUserCog,
  trainees: LuUsers,
  stations: LuClipboardList,
  programme: LuFolderKanban,
};

/**
 * What is left before a first examination, as the canvas draws it: a grey
 * panel, a progress bar and one tile per step.
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
    <section className="rounded-osce-2xl bg-canvas p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex min-w-0 flex-col gap-1">
          <p className={b2bTokens.b2bEyebrow}>
            Setup · {progress.done} of {progress.total} done
          </p>
          <h2 className="text-osce-title font-semibold text-b2b-headline">
            Getting started
          </h2>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-b2b-border sm:w-[200px]">
          <div
            className="h-full rounded-full bg-b2b-accent transition-[width] duration-500 ease-out"
            style={{ width: `${progress.percent}%` }}
          />
        </div>
      </div>

      <ol className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step) => {
          const Icon = step.done ? LuCheck : (STEP_ICONS[step.key] ?? LuClipboardList);
          return (
            <li key={step.key}>
              <Link
                href={hrefFor(step.path)}
                className="flex h-full flex-col gap-1 rounded-panel bg-b2b-surface p-4 transition-colors hover:bg-b2b-surface/70"
              >
                <span className="mb-2 flex h-8 w-8 items-center justify-center rounded-control bg-canvas text-b2b-graphite">
                  <Icon className="h-4 w-4" aria-hidden />
                </span>
                <span className="text-osce-body font-medium text-b2b-headline">{step.label}</span>
                <span className="text-osce-meta text-b2b-mid">{step.done ? "Done" : step.hint}</span>
              </Link>
            </li>
          );
        })}
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
  ];

  return (
    <section aria-label="At a glance" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {tiles.map((tile) => (
        <Link key={tile.label} href={hrefFor(tile.path)} className={b2bTokens.b2bStatCard}>
          <span className={b2bTokens.b2bEyebrow}>{tile.label}</span>
          <span className={b2bTokens.b2bStatCardValue}>{tile.value}</span>
        </Link>
      ))}
    </section>
  );
}
