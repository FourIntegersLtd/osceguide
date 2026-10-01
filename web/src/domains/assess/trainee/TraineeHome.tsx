"use client";

import Link from "next/link";
import {
  HiChevronRight,
  HiOutlineAcademicCap,
  HiOutlineCalendarDays,
  HiOutlineClipboardDocumentList,
  HiOutlineQueueList,
  HiOutlineSparkles,
} from "react-icons/hi2";
import type { IconType } from "react-icons";
import { Alert, AsyncBoundary, Badge, EmptyState, b2bTokens } from "@/foundation/ui";
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
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-b2b-border pb-4">
        <div className="min-w-0">
          <p className={b2bTokens.b2bEyebrow}>{greeting(new Date())}</p>
          <h1 className={`mt-1 ${b2bTokens.b2bPageTitle}`}>
            {name ? `Hello, ${name}.` : "Hello."}
          </h1>
          <p className={`mt-1 ${b2bTokens.b2bHeroSubtitle} ${b2bTokens.b2bProseMeasure}`}>
            Pick up an examination or practice circuit, or read back a station you have finished.
          </p>
        </div>
        <Badge tone={stream.connected ? "success" : "neutral"}>
          {stream.connected ? "Live" : "Updating"}
        </Badge>
      </header>

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
        <section aria-label="Your progress" className="space-y-2">
          <p className={b2bTokens.b2bEyebrow}>At a glance</p>
          <div className="flex flex-wrap gap-3">
            <Stat label="Rostered sittings" value={sittings.length} />
            <Stat label="Stations completed" value={stationsCompleted(sittings)} />
            <Stat label="Open now" value={live.length} />
          </div>
        </section>
      ) : null}

      <section aria-label="Your sittings" className="space-y-2">
        <p className={b2bTokens.b2bEyebrow}>Your sittings</p>
        {ordered.length === 0 ? (
          <EmptyState
            title="You are not booked on anything yet"
            description="When your organisation adds you to a sitting it appears here, and you are told when it opens."
          />
        ) : (
          <div className={b2bTokens.b2bGroupedShell}>
            {ordered.map((sitting) => (
              <SittingRow key={`${sitting.id}-${sitting.circuit_id}`} sitting={sitting} />
            ))}
          </div>
        )}
      </section>

      <Explore />
    </>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className={b2bTokens.b2bStatCard}>
      <p className={b2bTokens.b2bStatCardLabel}>{label}</p>
      <p className={b2bTokens.b2bStatCardValue}>{value}</p>
    </div>
  );
}

function SittingRow({ sitting }: { sitting: MySitting }) {
  const { hrefFor } = useSurface();
  const { completed, total } = progressOf(sitting);

  return (
    <Link href={hrefFor(`/trainee/sittings/${sitting.id}`)} className={b2bTokens.b2bGroupedRow}>
      <span
        className={`${b2bTokens.b2bIconChipBase} ${
          isExam(sitting)
            ? b2bTokens.b2bChipHueClasses.violet
            : b2bTokens.b2bChipHueClasses.blue
        }`}
      >
        {isExam(sitting) ? (
          <HiOutlineAcademicCap className="h-5 w-5" aria-hidden />
        ) : (
          <HiOutlineCalendarDays className="h-5 w-5" aria-hidden />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className={b2bTokens.b2bGroupedRowTitle}>{sitting.name}</p>
          {sitting.can_join ? <Badge tone="success">Open now</Badge> : null}
          {sitting.paused ? <Badge tone="warning">Paused</Badge> : null}
        </div>
        <p className={b2bTokens.b2bGroupedRowSubtitle}>{summaryLine(sitting)}</p>
        <p className="mt-0.5 text-osce-caption text-b2b-mid">
          {continueLabel(sitting)}
          {total > 0 ? ` · ${completed}/${total}` : ""}
        </p>
      </div>
      <HiChevronRight className="h-5 w-5 shrink-0 text-b2b-inactive" aria-hidden />
    </Link>
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
    <section aria-label="Explore" className="space-y-2">
      <p className={b2bTokens.b2bEyebrow}>Explore</p>
      <div className={b2bTokens.b2bGroupedShell}>
        <ExploreRow
          href={hrefFor("/trainee/practice")}
          icon={HiOutlineSparkles}
          hue="amber"
          title="Self practice"
          subtitle="Sit a station your organisation has published, on your own."
        />
        <ExploreRow
          href={hrefFor("/stations")}
          icon={HiOutlineQueueList}
          hue="teal"
          title="Station library"
          subtitle="Browse every scenario published for your exams."
        />
        <ExploreRow
          href={hrefFor("/transcripts")}
          icon={HiOutlineClipboardDocumentList}
          hue="blue"
          title="Consultation records"
          subtitle="Read back what was said in a station you have finished."
        />
      </div>
    </section>
  );
}

function ExploreRow({
  href,
  icon: Icon,
  hue,
  title,
  subtitle,
}: {
  href: string;
  icon: IconType;
  hue: b2bTokens.B2BChipHue;
  title: string;
  subtitle: string;
}) {
  return (
    <Link href={href} className={b2bTokens.b2bGroupedRow}>
      <span className={`${b2bTokens.b2bIconChipBase} ${b2bTokens.b2bChipHueClasses[hue]}`}>
        <Icon className="h-5 w-5" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <p className={b2bTokens.b2bGroupedRowTitle}>{title}</p>
        <p className={b2bTokens.b2bGroupedRowSubtitle}>{subtitle}</p>
      </div>
      <HiChevronRight className="h-5 w-5 shrink-0 text-b2b-inactive" aria-hidden />
    </Link>
  );
}
