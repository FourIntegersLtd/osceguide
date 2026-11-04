"use client";

import Link from "next/link";
import {
  HiOutlineAcademicCap,
  HiOutlineCalendarDays,
  HiOutlineClock,
  HiOutlineSparkles,
} from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  B2CGroupedRowLink,
  B2CGroupedSection,
  B2CPageHeader,
  Badge,
  EmptyState,
} from "@/foundation/ui";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { activeMembership, useSession } from "@/foundation/session";
import { capabilitiesFor, useSurface } from "@/capabilities";
import { LiveTurnBanner } from "@/domains/assess/trainee/LiveTurnBanner";
import {
  mySittingsStreamPath,
  readMySittings,
  type MySitting,
  type MySittings,
} from "@/domains/assess/trainee/api";
import {
  continueLabel,
  firstName,
  greeting,
  isExam,
  liveSittings,
  progressOf,
  sittingForSlot,
  slotById,
  sortSittings,
  splitFinished,
  summaryLine,
} from "@/domains/assess/trainee/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * What a rostered person sees: everything they are down to sit, pushed live.
 *
 * The join decision is the backend's — `can_join` — not a status string read
 * here. A candidate entering a station that is not theirs, or not yet open, is
 * the kind of thing that has to be one decision in one place.
 *
 * The stream is the screen's normal source and the plain read is only its
 * first frame, which is why a dropped connection shows "Updating" rather than
 * emptying the page.
 */
export function TraineeHome({ slotId = null }: { slotId?: string | null }) {
  const { session } = useSession();
  const { orgSlug } = useSurface();
  const initial = useAsync((signal) => readMySittings(orgSlug, signal), [orgSlug]);
  const stream = useEventStream<MySittings>(mySittingsStreamPath(orgSlug));
  const data = stream.data ?? initial.data;
  const name = firstName(session?.user.name);

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <B2CPageHeader
        className="!mb-0"
        eyebrow={activeMembership(session)?.org_name ?? greeting(new Date())}
        title={name ? `Hello, ${name}.` : "Hello."}
        action={
          <Badge variant={stream.connected ? "success" : "neutral"} dot>
            {stream.connected ? "Live" : "Updating"}
          </Badge>
        }
      />

      <AsyncBoundary state={initial}>
        {() => <Overview sittings={data?.items ?? []} slotId={slotId} />}
      </AsyncBoundary>
    </div>
  );
}

function Overview({
  sittings,
  slotId,
}: {
  sittings: readonly MySitting[];
  slotId: string | null;
}) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const live = liveSittings(sittings);
  const { current, past } = splitFinished(sortSittings(sittings));
  // An emailed join link named a slot, and only the list this person has
  // already loaded can say which sitting owns it. Not finding it is an answer
  // rather than a fault: the slot was taken off them, or the link was never
  // theirs, and either way what follows is still the truth.
  const sentTo = sittingForSlot(sittings, slotId);
  const station = sentTo ? (slotById(sentTo, slotId)?.station_title ?? null) : null;

  return (
    <>
      {slotId ? (
        sentTo ? (
          <Alert tone="info">
            You were sent to {station ?? "one of your stations"} on {sentTo.name}.{" "}
            <Link className="underline" href={hrefFor(`/trainee/sittings/${sentTo.id}`)}>
              Open it
            </Link>
            {sentTo.can_join ? ". The room is open now." : "."}
          </Alert>
        ) : (
          <Alert tone="warning">
            That link is for a station you are no longer booked on. Everything you are booked on is listed below.
          </Alert>
        )
      ) : null}
      <LiveTurnBanner sittings={live} />

      <section aria-label={`Your ${w.sittings}`}>
        {current.length === 0 && past.length === 0 ? (
          <EmptyState
            title="You are not booked on anything yet"
            description={`When your organisation adds you, your ${w.sittings} appear here, and you are told when one opens.`}
          />
        ) : (
          <B2CGroupedSection eyebrow={`Your ${w.sittings}`}>
            {current.map((sitting) => (
              <SittingRow key={`${sitting.id}-${sitting.circuit_id}`} sitting={sitting} />
            ))}
          </B2CGroupedSection>
        )}
        {past.length > 0 ? (
          <B2CGroupedSection eyebrow={`Past ${w.sittings}`}>
            {past.map((sitting) => (
              <SittingRow key={`${sitting.id}-${sitting.circuit_id}`} sitting={sitting} />
            ))}
          </B2CGroupedSection>
        ) : null}
      </section>

      <Explore />
    </>
  );
}

function SittingRow({ sitting }: { sitting: MySitting }) {
  const { hrefFor } = useSurface();
  const { completed, total } = progressOf(sitting);

  return (
    <B2CGroupedRowLink
      href={hrefFor(`/trainee/sittings/${sitting.id}`)}
      icon={isExam(sitting) ? HiOutlineAcademicCap : HiOutlineCalendarDays}
      title={sitting.name}
      meta={`${summaryLine(sitting)} · ${continueLabel(sitting)}${
        total > 0 ? ` · ${completed}/${total}` : ""
      }`}
      trailing={
        sitting.can_join ? (
          <Badge variant="success" dot>
            Open now
          </Badge>
        ) : sitting.released ? (
          <Badge variant="success" dot>
            Result released
          </Badge>
        ) : sitting.paused ? (
          <Badge variant="warning" dot>
            Paused
          </Badge>
        ) : null
      }
    />
  );
}

/**
 * The rest of the arm, named.
 *
 * Self practice is this domain's; the practice history is a capability
 * mounted on this surface, reached through `hrefFor`. An institution's trainee
 * has no personal-practice workspace to be sent to.
 */
function Explore() {
  const { hrefFor, surface } = useSurface();
  const { session } = useSession();
  const mounted = capabilitiesFor(surface, { can: session?.capabilities.can ?? {} }).map((c) => c.id);

  return (
    <>
      <B2CGroupedSection eyebrow="Practise">
        <B2CGroupedRowLink
          href={hrefFor("/trainee/practice")}
          icon={HiOutlineSparkles}
          title="Self practice"
          meta="From your organisation"
        />
        {/* Only what this workspace mounts: a link to a page it does not would open a 404. */}
        {/* Every practice attempt, with its transcript and debrief, from the list the person already owns (T-5). */}
        {mounted.includes("transcripts") ? (
          <B2CGroupedRowLink
            href={hrefFor("/transcripts")}
            icon={HiOutlineClock}
            title="Practice history"
            meta="Past attempts, transcripts and debriefs"
          />
        ) : null}
      </B2CGroupedSection>
    </>
  );
}
