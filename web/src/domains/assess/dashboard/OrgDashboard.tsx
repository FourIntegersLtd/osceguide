"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  LuCalendarDays,
  LuPlus,
} from "react-icons/lu";
import {
  AsyncBoundary,
  B2CGroupedRow,
  B2CGroupedRowLink,
  B2CGroupedSection,
  B2CPageHeader,
  Badge,
  ButtonLink,
  StepGuide,
  b2bTokens,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { readOrgDashboard, type OrgDashboard as Data } from "@/domains/assess/dashboard/api";
import { LiveNow } from "@/domains/assess/dashboard/LiveNow";
import { SupervisorCircuits } from "@/domains/assess/dashboard/SupervisorCircuits";
import { nextSetupAction, setupSteps } from "@/domains/assess/dashboard/support";
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
  const step = nextSetupAction(data.setup, can(session, "author_content"));
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

      <Setup data={data} />

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

/**
 * What is left before a first sitting, in build order: the one thing to do
 * next, then every step with where it stands. It goes away once all are done.
 *
 * `ready_to_run` stays the backend's judgement of whether a sitting can be
 * scheduled; this is the longer road to a fully built institution.
 */
function Setup({ data }: { data: Data }) {
  const { hrefFor } = useSurface();
  const router = useRouter();
  const steps = setupSteps(data.setup);
  const { session } = useSession();
  const next = nextSetupAction(data.setup, can(session, "author_content"));
  if (!next) return null;

  return (
    <section className="flex flex-col gap-4 rounded-osce-2xl bg-canvas p-6">
      <h2 className="text-osce-title font-semibold text-b2b-headline">Getting started</h2>
      <StepGuide
        steps={steps}
        current={next.step}
        onSelect={(id) => router.push(hrefFor(steps.find((step) => step.id === id)!.path))}
        line={next.line}
      >
        <ButtonLink href={hrefFor(next.path)} themeType="b2b" variant="commit">
          {next.label}
        </ButtonLink>
      </StepGuide>
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
