"use client";

import Link from "next/link";
import { Alert, AsyncBoundary, ButtonLink, EmptyState } from "@/foundation/ui";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { activeMembership, useSession } from "@/foundation/session";
import { capabilitiesFor, useSurface } from "@/capabilities";
import { LiveTurnBanner } from "@/domains/assess/trainee/LiveTurnBanner";
import { boardChip } from "@/foundation/ui/boardKit";
import {
  mySittingsStreamPath,
  readMyResult,
  readMySittings,
  type MySitting,
  type MySittings,
} from "@/domains/assess/trainee/api";
import {
  continueLabel,
  firstName,
  greeting,
  liveSittings,
  sittingForSlot,
  slotById,
  sortSittings,
  splitFinished,
  summaryLine,
} from "@/domains/assess/trainee/support";
import {
  TraineeHead,
  TraineeHero,
  TraineeList,
  TraineePage,
  TraineeRowLink,
} from "@/domains/assess/trainee/traineeBoard";
import { useAssessWords } from "@/capabilities/assess-words";
import { sittingWhen } from "@/domains/assess/sittingWords";
import {
  BROWSER_NOTICE,
  homeDesc,
  homeEmpty,
  homeHero,
  releasedEyebrow,
} from "@/domains/assess/trainee/hireCopy";
import { isOver } from "@/domains/assess/trainee/support";

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
  const w = useAssessWords();
  const { orgSlug } = useSurface();
  const initial = useAsync(
    (signal) => readMySittings(orgSlug, signal),
    [orgSlug],
  );
  const stream = useEventStream<MySittings>(mySittingsStreamPath(orgSlug));
  const data = stream.data ?? initial.data;
  const name = firstName(session?.user.name);
  const org = activeMembership(session)?.org_name ?? null;

  return (
    <TraineePage label={w.MyTraining}>
      <TraineeHead
        eyebrow={org ?? greeting(new Date())}
        title={w.hiring ? w.MyTraining : name ? `Hello, ${name}.` : "Hello."}
        desc={w.hiring ? homeDesc(org ?? "your employer") : undefined}
        acts={
          <span className={boardChip(stream.connected ? "ok" : "neutral")}>
            {stream.connected ? "Live" : "Updating"}
          </span>
        }
      />

      <AsyncBoundary state={initial}>
        {() => <Overview sittings={data?.items ?? []} slotId={slotId} org={org ?? "your employer"} />}
      </AsyncBoundary>
    </TraineePage>
  );
}

function Overview({
  sittings,
  slotId,
  org,
}: {
  sittings: readonly MySitting[];
  slotId: string | null;
  org: string;
}) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const { surface } = useSurface();
  const live = liveSittings(sittings);
  const split = splitFinished(sortSittings(sittings));
  const { past } = split;
  // An employer's candidate gets one hero for what is next; the list keeps only what the hero does not name.
  const hero = w.hiring ? homeHero(sittings) : null;
  // The released result's own date says "Released today" or just "Released".
  const releasedOn = useAsync(
    (signal) => (hero?.kind === "result" ? readMyResult(hero.path.split("/").pop() ?? "", signal) : Promise.resolve(null)),
    [hero?.kind, hero?.path],
  );
  const current =
    hero?.kind === "upcoming"
      ? split.current.filter((s) => !hero.path.endsWith(`/${s.id}`))
      : split.current;
  const hasAny = split.current.length > 0 || past.length > 0;
  // An emailed join link named a slot, and only the list this person has
  // already loaded can say which sitting owns it. Not finding it is an answer
  // rather than a fault: the slot was taken off them, or the link was never
  // theirs, and either way what follows is still the truth.
  const sentTo = sittingForSlot(sittings, slotId);
  const station = sentTo
    ? (slotById(sentTo, slotId)?.station_title ?? null)
    : null;

  return (
    <>
      {slotId ? (
        sentTo ? (
          <Alert tone="info">
            You were sent to {station ?? "one of your stations"} on{" "}
            {sentTo.name}.{" "}
            <Link
              className="underline"
              href={hrefFor(`/trainee/sittings/${sentTo.id}`)}
            >
              Open it
            </Link>
            {sentTo.can_join ? ". The room is open now." : "."}
          </Alert>
        ) : (
          <Alert tone="warning">
            That link is for a station you are no longer booked on. Everything
            you are booked on is listed below.
          </Alert>
        )
      ) : null}
      <LiveTurnBanner sittings={live} />
      {hero ? (
        <TraineeHero
          eyebrow={hero.kind === "result" ? releasedEyebrow(releasedOn.data?.released_at) : hero.eyebrow}
          title={hero.title}
          size="lg"
          action={
            <ButtonLink themeType="b2b" variant="commit" href={hrefFor(hero.path)}>
              {hero.label}
            </ButtonLink>
          }
        >
          {hero.meta}
        </TraineeHero>
      ) : null}
      {w.hiring && (hero?.kind === "upcoming" || live.length > 0) ? (
        <Alert tone="info">{BROWSER_NOTICE}</Alert>
      ) : null}

      {!hasAny ? (
        <EmptyState
          {...(w.hiring
            ? homeEmpty(org)
            : {
                title: "You are not booked on anything yet",
                description: `When your organisation adds you, your ${w.sittings} appear here, and you are told when one opens.`,
              })}
        />
      ) : (
        <>
          {current.length > 0 ? (
            <TraineeList
              title={`Your ${w.sittings}`}
              label={`Your ${w.sittings}`}
            >
              {current.map((sitting) => (
                <SittingRow
                  key={`${sitting.id}-${sitting.circuit_id}`}
                  sitting={sitting}
                />
              ))}
            </TraineeList>
          ) : null}
          {past.length > 0 ? (
            <TraineeList title={`Past ${w.sittings}`}>
              {past.map((sitting) => (
                <SittingRow
                  key={`${sitting.id}-${sitting.circuit_id}`}
                  sitting={sitting}
                />
              ))}
            </TraineeList>
          ) : null}
        </>
      )}

      {surface === "hire" ? null : <Explore />}
    </>
  );
}

function SittingRow({ sitting }: { sitting: MySitting }) {
  const { hrefFor } = useSurface();
  const w = useAssessWords();

  return (
    <TraineeRowLink
      href={hrefFor(`/trainee/sittings/${sitting.id}`)}
      title={sitting.name}
      meta={
        w.hiring && isOver(sitting)
          ? sittingWhen(sitting.scheduled_for)
          : `${summaryLine(sitting, w)} · ${continueLabel(sitting, w)}`
      }
    >
      {sitting.can_join ? (
        <span className={boardChip("ok")}>Open now</span>
      ) : sitting.released ? (
        <span className={boardChip("ok")}>Result released</span>
      ) : sitting.paused ? (
        <span className={boardChip("warn")}>Paused</span>
      ) : null}
    </TraineeRowLink>
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
  const mounted = capabilitiesFor(surface, {
    can: session?.capabilities.can ?? {},
    includeHidden: true,
  }).map((c) => c.id);

  return (
    <TraineeList title="Practise">
      <TraineeRowLink
        href={hrefFor("/trainee/practice")}
        title="Self practice"
        meta="From your organisation"
      />
      <TraineeRowLink
        href={hrefFor("/mocks")}
        title="Practice sessions"
        meta="Practice sets you work through, station by station"
      />
      {/* Only what this workspace mounts: a link to a page it does not would open a 404. */}
      {/* Every practice attempt, with its transcript and debrief, from the list the person already owns (T-5). */}
      {mounted.includes("transcripts") ? (
        <TraineeRowLink
          href={hrefFor("/transcripts")}
          title="Practice history"
          meta="Past attempts, transcripts and debriefs"
        />
      ) : null}
    </TraineeList>
  );
}
