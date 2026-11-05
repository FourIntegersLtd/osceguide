"use client";

import Link from "next/link";
import { LuCalendarDays, LuChevronRight, LuPlus } from "react-icons/lu";
import {
  Alert,
  AsyncBoundary,
  B2CGroupedRow,
  B2CGroupedRowLink,
  B2CGroupedSection,
  B2CPageHeader,
  Badge,
  Button,
  ButtonLink,
  Spinner,
  StatGrid,
  StatTile,
  b2bTokens,
} from "@/foundation/ui";
import { humanise } from "@/foundation/format";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { readOrgDashboard, type OrgDashboard as Data } from "@/domains/assess/dashboard/api";
import { LiveNow } from "@/domains/assess/dashboard/LiveNow";
import { SetupAssistant } from "@/domains/assess/dashboard/SetupAssistant";
import { SupervisorCircuits } from "@/domains/assess/dashboard/SupervisorCircuits";
import {
  assistantSteps,
  attentionFromResults,
  comingUp,
  modeLabel,
  setupComplete,
  type AttentionItem,
} from "@/domains/assess/dashboard/support";
import { readResultsIndex } from "@/domains/assess/results/api";
import { greetingFor } from "@/domains/assess/trainee/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * The institution's home screen.
 *
 * Until a first sitting is possible an administrator sees the setup assistant; afterwards
 * "Today". A supervisor's circuits show for whoever may run them, so a supervisor who is also
 * an admin sees both halves rather than whichever a role check picked.
 */
export function OrgDashboard({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => readOrgDashboard(orgSlug, signal), [orgSlug]);
  const { session } = useSession();
  const admin = can(session, "manage_team");
  const runs = can(session, "run_circuits");

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <AsyncBoundary state={state}>
        {(data) => <Body data={data} orgSlug={orgSlug} admin={admin} runs={runs} />}
      </AsyncBoundary>
    </div>
  );
}

function Body({ data, orgSlug, admin, runs }: { data: Data; orgSlug: string; admin: boolean; runs: boolean }) {
  const w = useAssessWords();
  const { session } = useSession();
  const settingUp = admin && !setupComplete(assistantSteps(data.setup, w));

  if (settingUp) {
    return (
      <>
        <SetupAssistant orgName={data.name} setup={data.setup} />
        <Counts data={data} />
      </>
    );
  }
  return <Today data={data} orgSlug={orgSlug} admin={admin} runs={runs} name={session?.user.name} />;
}

function Today({ data, orgSlug, admin, runs, name }: { data: Data; orgSlug: string; admin: boolean; runs: boolean; name?: string }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const { session } = useSession();
  const schedules = can(session, "schedule_sittings");
  const upcoming = comingUp(data.recent_sittings ?? []);
  const earlier = (data.recent_sittings ?? []).filter((sitting) => sitting.status !== "scheduled");

  return (
    <>
      <B2CPageHeader
        className="!mb-0"
        eyebrow={data.name}
        title={greetingFor(name, new Date())}
        action={
          schedules ? (
            data.setup.ready_to_run ? (
              <ButtonLink href={hrefFor("/sittings/new")} themeType="b2b" variant="commit">
                <LuPlus className="h-4 w-4" aria-hidden />
                {w.scheduleSitting}
              </ButtonLink>
            ) : (
              <div className="flex flex-col items-end gap-1">
                <Button themeType="b2b" variant="commit" disabled aria-describedby="schedule-blocked">
                  {w.scheduleSitting}
                </Button>
                <p id="schedule-blocked" className="text-osce-meta text-b2b-muted">
                  {`Nothing can be scheduled until an ${w.exam} is ready. `}
                  <Link href={hrefFor("/authoring")} className={b2bTokens.b2bLink}>
                    {`Set up an ${w.exam}`}
                  </Link>
                </p>
              </div>
            )
          ) : null
        }
      />

      {/* What is happening now comes before what exists: on an examination morning it is the
          only thing anybody wants. */}
      {runs ? <LiveNow orgSlug={orgSlug} /> : null}

      {can(session, "sign_off_results") ? <NeedsAttention orgSlug={orgSlug} /> : null}

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start [&>*]:min-w-0 [&>*]:flex-1">
        {/* SLOT (Phase 5): "Stations to review" for a supervisor, grouped by circuit, comes from a
            results component that phase exposes. Until then SupervisorCircuits names the circuits
            this person leads and links on to Results. */}
        {runs ? <SupervisorCircuits orgSlug={orgSlug} sayWhenEmpty={!admin} /> : null}

        <B2CGroupedSection
          eyebrow="Coming up"
          action={
            <Link href={hrefFor("/sittings")} className={b2bTokens.b2bLink}>
              {`All ${w.sittings}`}
            </Link>
          }
        >
          {upcoming.length === 0 ? (
            <B2CGroupedRow
              title={`No ${w.sittings} are scheduled.`}
              meta={schedules ? <Link href={hrefFor("/sittings/new")} className={b2bTokens.b2bLink}>{w.scheduleSitting}</Link> : `An administrator can schedule one.`}
            />
          ) : (
            upcoming.map((sitting) => <SittingRow key={sitting.id} sitting={sitting} />)
          )}
        </B2CGroupedSection>
      </div>

      {earlier.length > 0 ? (
        <B2CGroupedSection eyebrow={`Recent ${w.sittings}`}>
          {earlier.map((sitting) => (
            <SittingRow key={sitting.id} sitting={sitting} />
          ))}
        </B2CGroupedSection>
      ) : null}

      {admin ? <Counts data={data} /> : null}
    </>
  );
}

function SittingRow({ sitting }: { sitting: NonNullable<Data["recent_sittings"]>[number] }) {
  const { hrefFor } = useSurface();
  return (
    <B2CGroupedRowLink
      href={hrefFor(`/sittings/${sitting.id}`)}
      icon={LuCalendarDays}
      title={sitting.name}
      meta={
        sitting.scheduled_for
          ? `${new Date(sitting.scheduled_for).toLocaleString()} · ${modeLabel(sitting.mode)}`
          : modeLabel(sitting.mode)
      }
      trailing={
        <Badge variant="neutral" dot>
          {humanise(sitting.status)}
        </Badge>
      }
    />
  );
}

/**
 * Decisions waiting and results ready to release, oldest first, from the results index.
 * Trainees who have not joined are not here: no existing read lists them without paging the
 * whole roster, so People carries that.
 */
function NeedsAttention({ orgSlug }: { orgSlug: string }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => readResultsIndex(orgSlug, signal), [orgSlug]);
  if (state.loading) return <Spinner />;
  if (state.error) return <Alert tone="danger">{errorMessage(state.error)}</Alert>;
  const items: AttentionItem[] = attentionFromResults(state.data?.rows ?? [], w);

  return (
    <B2CGroupedSection eyebrow="Needs your attention">
      {items.length === 0 ? (
        <B2CGroupedRow
          title="Nothing needs you right now."
          meta={
            <Link href={hrefFor("/results")} className={b2bTokens.b2bLink}>
              Open Results
            </Link>
          }
        />
      ) : (
        items.map((item) => (
          <B2CGroupedRowLink
            key={item.key}
            href={hrefFor(item.href)}
            icon={LuChevronRight}
            title={item.title}
            meta={item.body}
            trailing={<Badge variant="warning" dot>{item.tag}</Badge>}
          />
        ))
      )}
    </B2CGroupedSection>
  );
}

function Counts({ data }: { data: Data }) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const counts = data.counts;
  const tiles = [
    { label: `${w.Exams} ready to schedule`, value: counts.programmes_with_markable_exam, path: "/authoring" },
    // The backend counts this organisation's own stations, not the platform catalogue it may also run.
    { label: "Published stations", value: counts.stations, path: "/authoring/stations" },
    { label: w.Trainees, value: counts.trainees, path: "/trainees" },
    { label: w.Supervisors === "Assessors" ? "Assessors" : "Staff", value: counts.staff, path: "/team" },
    { label: w.Sittings, value: counts.sittings, path: "/sittings" },
  ];

  return (
    <StatGrid label="At a glance">
      {tiles.map((tile) => (
        <StatTile key={tile.label} label={tile.label} value={tile.value} href={hrefFor(tile.path)} />
      ))}
    </StatGrid>
  );
}
