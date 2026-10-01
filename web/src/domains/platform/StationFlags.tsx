"use client";

import { Fragment, useState } from "react";
import { LuFlag } from "react-icons/lu";
import {
  Alert,
  AsyncBoundary,
  B2CSegmentedTabs,
  Badge,
  Button,
  Panel,
  PlatformPageHeader,
  Row,
  RowList,
  Textarea,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import {
  decideStationFlag,
  listStationFlags,
  type StationFlag,
} from "@/domains/platform/api";
import { formatMoment } from "@/domains/platform/support";

type FlagFilter = "open" | "resolved" | "all";

const FILTERS: B2CSegmentedTabItem<FlagFilter>[] = [
  { id: "open", label: "Open" },
  { id: "resolved", label: "Answered" },
  { id: "all", label: "Everything" },
];

/**
 * What readers have reported about the cases they sit, and what we said.
 *
 * The console half of a report. A learner's flag used to land nowhere at all —
 * the route answered 204 and discarded the body, with persistence marked TODO —
 * while the button went on thanking them. This is the screen that makes that
 * "our team will take a look at this" true, and the only place the reports were
 * ever visible to anybody who could act on one.
 *
 * Oldest first: the report that has waited longest is the one a reader is
 * still waiting on. Grouped by nothing, because three people reporting one case
 * is three data points, and a queue that folds them together loses the signal
 * that decides whether the case gets re-reviewed.
 */
export function StationFlags() {
  const [status, setStatus] = useState<FlagFilter>("open");
  const queue = useAsync(
    (signal) =>
      listStationFlags({ status: status === "all" ? null : status }, signal),
    [status],
  );
  const [editing, setEditing] = useState<StationFlag | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const decide = async (
    flag: StationFlag,
    input: { status: "open" | "resolved"; note?: string | null },
  ) => {
    setBusy(true);
    setFailure(null);
    try {
      await decideStationFlag(flag.id, input);
      setEditing(null);
      setNote("");
      queue.reload();
    } catch (cause) {
      setFailure(
        errorMessage(cause instanceof Error ? cause : new Error(String(cause))),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="Station reports"
        description="Cases readers said were wrong, and what was done about them."
        icon={LuFlag}
      />
      {failure ? <Alert tone="danger">{failure}</Alert> : null}
      <Panel
        title="Reports"
        description="Closed reports stay listed, so if someone reports the same thing again you can see it was already checked."
        actions={
          <B2CSegmentedTabs
            items={FILTERS}
            value={status}
            onChange={setStatus}
            compact
            aria-label="Report status"
          />
        }
        padding="none"
      >
        <AsyncBoundary
          state={queue}
          isEmpty={(page) => page.items.length === 0}
          empty={{
            title: status === "open" ? "Nothing reported" : "Nothing here",
            description:
              status === "open"
                ? "Every report we have is answered."
                : "No reports match this filter yet.",
            bare: true,
          }}
        >
          {(page) => (
            <RowList flush>
              {page.items.map((flag) => (
                <Fragment key={flag.id}>
                  <Row>
                    <div className="min-w-0">
                      <p className="text-osce-data font-medium text-ink">
                        {flag.station_title ?? "A station we no longer have"}
                      </p>
                      <p className="truncate text-osce-meta text-ink-subtle">
                        {flag.reporter_name ?? "Someone"} · reported{" "}
                        {formatMoment(flag.created_at)}
                        {flag.resolved_at
                          ? ` · answered ${formatMoment(flag.resolved_at)}`
                          : ""}
                      </p>
                      {flag.resolution_note ? (
                        <p className="mt-1 text-osce-meta text-ink-muted">
                          {flag.resolution_note}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge
                        tone={flag.status === "open" ? "warning" : "success"}
                      >
                        {flag.status === "open" ? "Open" : "Answered"}
                      </Badge>
                      {flag.status === "open" ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={busy}
                          onClick={() => {
                            setEditing(flag);
                            setNote("");
                          }}
                        >
                          Answer
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={busy}
                          onClick={() => void decide(flag, { status: "open" })}
                        >
                          Reopen
                        </Button>
                      )}
                    </div>
                  </Row>
                  {editing?.id === flag.id ? (
                    <Row className="flex-col items-stretch">
                      <form
                        onSubmit={(event) => {
                          event.preventDefault();
                          void decide(editing, {
                            status: "resolved",
                            note: note.trim() || null,
                          });
                        }}
                        className="flex flex-col gap-3"
                      >
                        <p className="text-osce-data font-medium text-ink">
                          Answer:{" "}
                          {editing.station_title ??
                            "a station we no longer have"}
                        </p>
                        <Textarea
                          label="What was done"
                          value={note}
                          maxLength={2000}
                          placeholder="Fixed in version 3. / Deliberate: the brief reads this way on purpose."
                          onChange={(event) => setNote(event.target.value)}
                        />
                        <div className="flex items-center gap-2">
                          <Button
                            type="submit"
                            variant="primary"
                            size="sm"
                            isLoading={busy}
                          >
                            Mark answered
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditing(null)}
                          >
                            Cancel
                          </Button>
                        </div>
                      </form>
                    </Row>
                  ) : null}
                </Fragment>
              ))}
            </RowList>
          )}
        </AsyncBoundary>
      </Panel>
    </div>
  );
}
