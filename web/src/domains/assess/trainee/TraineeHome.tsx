"use client";

import Link from "next/link";
import {
  HiOutlineAcademicCap,
  HiOutlineCalendarDays,
  HiOutlineClipboardDocumentList,
  HiOutlineQueueList,
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
  b2bTokens,
} from "@/foundation/ui";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { LiveTurnBanner } from "@/domains/assess/trainee/LiveTurnBanner";
import {
  MY_SITTINGS_STREAM,
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
  stationsCompleted,
  summaryLine,
} from "@/domains/assess/trainee/support";

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
  const initial = useAsync((signal) => readMySittings(signal), []);
  const stream = useEventStream<MySittings>(MY_SITTINGS_STREAM);
  const data = stream.data ?? initial.data;
  const name = firstName(session?.user.name);

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <B2CPageHeader
        className="!mb-0"
        eyebrow={greeting(new Date())}
        title={name ? `Hello, ${name}.` : "Hello."}
        subtitle="Pick up an examination or practice circuit, or read back a station you have finished."
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
  const { hrefFor } = useSurface();
  const live = liveSittings(sittings);
  const ordered = sortSittings(sittings);
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

      {sittings.length > 0 ? (
        <section aria-label="Your progress" className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Stat label="Rostered sittings" value={sittings.length} />
          <Stat label="Stations completed" value={stationsCompleted(sittings)} />
          <Stat label="Open now" value={live.length} />
        </section>
      ) : null}

      <section aria-label="Your sittings">
        {ordered.length === 0 ? (
          <EmptyState
            title="You are not booked on anything yet"
            description="When your organisation adds you to a sitting it appears here, and you are told when it opens."
          />
        ) : (
          <B2CGroupedSection eyebrow="Your sittings">
            {ordered.map((sitting) => (
              <SittingRow key={`${sitting.id}-${sitting.circuit_id}`} sitting={sitting} />
            ))}
          </B2CGroupedSection>
        )}
      </section>

      <Explore />
    </>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className={b2bTokens.b2bStatCard}>
      <p className={b2bTokens.b2bEyebrow}>{label}</p>
      <p className={b2bTokens.b2bStatCardValue}>{value}</p>
    </div>
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
 * Self practice is this domain's; the station library and the transcripts are
 * capabilities mounted on this surface, reached through `hrefFor` so the paths
 * stay the surface's rather than being written down here.
 */
function Explore() {
  const { hrefFor } = useSurface();

  return (
    <B2CGroupedSection eyebrow="Explore">
      <B2CGroupedRowLink
        href={hrefFor("/trainee/practice")}
        icon={HiOutlineSparkles}
        title="Self practice"
        meta="Sit a station your organisation has published, on your own."
      />
      <B2CGroupedRowLink
        href={hrefFor("/stations")}
        icon={HiOutlineQueueList}
        title="Station library"
        meta="Browse every scenario published for your exams."
      />
      <B2CGroupedRowLink
        href={hrefFor("/transcripts")}
        icon={HiOutlineClipboardDocumentList}
        title="Consultation records"
        meta="Read back what was said in a station you have finished."
      />
    </B2CGroupedSection>
  );
}
