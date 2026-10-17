"use client";

import { useState } from "react";
import {
  Alert,
  AsyncBoundary,
  B2CGroupedRow,
  B2CGroupedSection,
  B2CHero,
  B2CPageHeader,
  B2CSegmentedTabs,
  Badge,
  Button,
  ButtonLink,
  LoadMore,
  Textarea,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { errorMessage, useCursorPages } from "@/foundation/hooks";
import { PERSONAL_SLUG } from "@/foundation/routing";
import { stationHref } from "@/capabilities/stations";
import {
  decideStationFlag,
  listStationFlags,
  type StationFlag,
} from "@/domains/platform/api";
import { oldestWaitedLine, openReportsHeadline } from "@/domains/platform/queues";
import { formatMoment } from "@/domains/platform/support";

type FlagFilter = "open" | "resolved" | "all";

const FILTERS: B2CSegmentedTabItem<FlagFilter>[] = [
  { id: "open", label: "Open" },
  { id: "resolved", label: "Answered" },
  { id: "all", label: "Everything" },
];

/** The station in the library, opened in the staff member's own workspace. */
const stationLink = (flag: StationFlag) =>
  stationHref((path) => `/app/${PERSONAL_SLUG}${path}`, flag.station_id);

const stationName = (flag: StationFlag) => flag.station_title ?? "A station we no longer have";

/**
 * What readers have reported about the cases they sit, and what we said.
 *
 * Oldest first: the report that has waited longest is the one a reader is
 * still waiting on. Grouped by nothing, because three people reporting one case
 * is three data points, and a queue that folds them together loses the signal
 * that decides whether the case gets re-reviewed. An answer is sent to the
 * reporter's inbox in the app; a closed report stays listed so a repeat report
 * shows it was already checked.
 */
function AnswerCard({
  flag,
  note,
  busy,
  onNote,
  onAnswer,
  onReopen,
  onClose,
}: {
  flag: StationFlag;
  note: string;
  busy: boolean;
  onNote: (value: string) => void;
  onAnswer: () => void;
  onReopen: () => void;
  onClose: () => void;
}) {
  const open = flag.status === "open";
  const reporter = flag.reporter_name ?? "The reporter";
  return (
    <B2CGroupedSection
      eyebrow={stationName(flag)}
      action={
        <span className="flex flex-wrap items-center gap-2">
          <ButtonLink href={stationLink(flag)} target="_blank" rel="noreferrer" variant="ghost" size="sm">
            Open station
          </ButtonLink>
          {open ? (
            <>
              <Button themeType="b2b" variant="commit" size="sm" isLoading={busy} onClick={onAnswer}>
                Send answer
              </Button>
              <Button variant="ghost" size="sm" disabled={busy} onClick={onClose}>
                Cancel
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" disabled={busy} onClick={onReopen}>
                Reopen
              </Button>
              <Button variant="ghost" size="sm" onClick={onClose}>
                Close
              </Button>
            </>
          )}
        </span>
      }
    >
      <B2CGroupedRow title={`${reporter} reported ${formatMoment(flag.created_at)}`} />
      <div className="flex flex-col gap-3 px-5 py-4">
        {flag.reason ? (
          <p className="whitespace-pre-wrap text-osce-body text-ink">
            <span className="font-medium">{reporter} said: </span>
            {flag.reason}
          </p>
        ) : null}
        {open ? (
          <Textarea
            label="Answer to the reporter"
            value={note}
            maxLength={2000}
            placeholder="Fixed in version 3. / Deliberate: the brief reads this way on purpose."
            hint={`${reporter} gets this in their inbox, with the station's name.`}
            onChange={(event) => onNote(event.target.value)}
          />
        ) : (
          <p className="whitespace-pre-wrap text-osce-body text-ink">
            {flag.resolution_note ?? "Answered without a note."}
          </p>
        )}
      </div>
    </B2CGroupedSection>
  );
}

export function StationFlags() {
  const [status, setStatus] = useState<FlagFilter>("open");
  const pages = useCursorPages(
    (cursor, signal) =>
      listStationFlags({ status: status === "all" ? null : status, cursor }, signal),
    [status],
  );
  const queue = pages.state;
  const [editing, setEditing] = useState<StationFlag | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const close = () => {
    setEditing(null);
    setNote("");
  };

  const decide = async (
    flag: StationFlag,
    input: { status: "open" | "resolved"; note?: string | null },
  ) => {
    setBusy(true);
    setFailure(null);
    try {
      await decideStationFlag(flag.id, input);
      close();
      queue.reload();
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  const hero = (flags: StationFlag[], hasMore: boolean) => (
    <B2CHero
      title={hasMore ? `More than ${openReportsHeadline(flags.length)}` : openReportsHeadline(flags.length)}
    >
      {oldestWaitedLine(flags[0]?.created_at) ?? "Every report we have is answered."}
    </B2CHero>
  );

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader title="Station reports" subtitle="Cases readers said were wrong." />
      {/* The headline counts the open queue, so it comes from the one read and only on that tab. */}
      {status === "open" ? (
        <AsyncBoundary state={queue}>{(flags) => hero(flags, pages.hasMore)}</AsyncBoundary>
      ) : null}
      {failure ? <Alert tone="danger">{failure}</Alert> : null}
      <B2CSegmentedTabs
        items={FILTERS}
        value={status}
        onChange={(next) => {
          setStatus(next);
          close();
        }}
        compact
        aria-label="Report status"
      />
      {editing ? (
        <AnswerCard
          flag={editing}
          note={note}
          busy={busy}
          onNote={setNote}
          onAnswer={() => decide(editing, { status: "resolved", note: note.trim() || null })}
          onReopen={() => decide(editing, { status: "open" })}
          onClose={close}
        />
      ) : null}
      <AsyncBoundary
        state={queue}
        isEmpty={(flags) => flags.length === 0}
        empty={{
          title: status === "open" ? "Nothing reported" : "Nothing here",
          description:
            status === "open"
              ? "Every report we have is answered."
              : "No reports match this filter yet.",
        }}
      >
        {(flags) => (
          <>
          <B2CGroupedSection eyebrow={FILTERS.find((f) => f.id === status)?.label}>
            {flags.map((flag) => (
              <B2CGroupedRow
                key={flag.id}
                active={editing?.id === flag.id}
                onClick={() => {
                  setEditing(flag);
                  setNote("");
                }}
                title={stationName(flag)}
                meta={`${flag.reporter_name ?? "Someone"} · reported ${formatMoment(flag.created_at)}${
                  flag.resolved_at ? ` · answered ${formatMoment(flag.resolved_at)}` : ""
                }`}
                trailing={
                  <Badge tone={flag.status === "open" ? "warning" : "success"}>
                    {flag.status === "open" ? "Open" : "Answered"}
                  </Badge>
                }
              />
            ))}
          </B2CGroupedSection>
          <LoadMore
            hasMore={pages.hasMore}
            busy={pages.loadingMore}
            onLoad={pages.loadMore}
            error={pages.moreError}
          />
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
