"use client";

import { useState } from "react";
import {
  Alert,
  AsyncBoundary,
  B2CHero,
  B2CSegmentedTabs,
  Badge,
  Button,
  FactList,
  Panel,
  PlatformPageHeader,
  Row,
  RowList,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { errorMessage, useAsync, useEventStream } from "@/foundation/hooks";
import {
  machineryStreamPath,
  readMachinery,
  reindexTutorMemory,
  type Machinery,
  type TutorMemoryReindex,
} from "@/domains/platform/support/api";
import { formatDetail, formatMoment, humanise, jobStatusTone, jobTaskLabel } from "@/domains/platform/support";

type JobStatus = "failed" | "todo" | "doing" | "succeeded";

const JOB_LABELS: Record<JobStatus, string> = {
  failed: "Failed",
  todo: "Waiting",
  doing: "Running",
  succeeded: "Succeeded",
};

/** procrastinate's status in the words the tabs use; an unknown one is still readable. */
function jobLabel(status: string): string {
  const labels: Record<string, string> = JOB_LABELS;
  return labels[status] ?? humanise(status);
}

const JOB_TABS: B2CSegmentedTabItem<JobStatus>[] = (
  Object.keys(JOB_LABELS) as JobStatus[]
).map((id) => ({ id, label: JOB_LABELS[id] }));

/** What procrastinate's event log says happened to a task, in words. */
const JOB_EVENT_LABELS: Record<string, string> = {
  deferred: "queued",
  started: "started",
  scheduled: "retry set",
  deferred_for_retry: "sent back",
  retried: "retried",
  failed: "failed",
  succeeded: "done",
  cancelled: "cancelled",
  aborted: "stopped",
};

/**
 * Is the platform working, not only up: the queue, the worker, the Cloud cap.
 *
 * Read once, then pushed: the stream re-sends the whole page every few seconds
 * and the moment a voice seat frees, so nothing here needs a reload.
 */
export function Ops() {
  const [status, setStatus] = useState<JobStatus>("failed");
  const initial = useAsync((signal) => readMachinery(status, signal), [status]);
  const stream = useEventStream<Machinery>(machineryStreamPath(status));
  // Straight after a tab switch the last frame is still the old tab's.
  const pushed = stream.data?.job_status === status ? stream.data : null;
  const machinery = { ...initial, data: pushed ?? initial.data };
  const health = { ...machinery, data: machinery.data?.health ?? null };
  const capacity = { ...machinery, data: machinery.data?.capacity ?? null };
  const jobs = { ...machinery, data: machinery.data?.jobs ?? null };

  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="System health"
        description="Pushed live from the platform."
        actions={
          <Badge tone={stream.connected ? "success" : "warning"}>
            {stream.connected ? "Live" : "Reconnecting"}
          </Badge>
        }
      />

      <AsyncBoundary state={machinery}>
        {(m) => <NowHero machinery={m} />}
      </AsyncBoundary>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
        <Panel title="Platform">
          <AsyncBoundary state={health}>
            {(h) => (
              <FactList
                items={[
                  { label: "Status", value: `${h.status} · v${h.version}` },
                  {
                    label: "Background tasks last checked in",
                    value: h.worker_seen_at
                      ? formatMoment(h.worker_seen_at)
                      : "Never",
                  },
                  {
                    label: "Checks",
                    value: Object.entries(h.checks)
                      .map(([name, result]) => `${name} ${result}`)
                      .join(" · "),
                  },
                  {
                    label: "Background tasks",
                    value:
                      Object.entries(h.jobs_by_status)
                        .filter(([, count]) => count > 0)
                        .map(([name, count]) => `${name} ${count}`)
                        .join(" · ") || "Empty",
                  },
                ]}
              />
            )}
          </AsyncBoundary>
        </Panel>

        <Panel title="Voice capacity">
          <AsyncBoundary state={capacity}>
            {(c) => (
              <FactList
                items={[
                  {
                    label: "Voice sessions (LiveKit Cloud)",
                    value:
                      c.active === null
                        ? "Unknown, so new sessions use our own servers"
                        : `${c.active} of ${c.max_concurrent} held · ${c.free} free`,
                  },
                  {
                    label: "Extra paid capacity",
                    value: c.overflow_enabled ? "On" : "Off",
                  },
                  {
                    label: "Our own servers",
                    value: `${c.self_hosted_seats_taken ?? "-"} of ${c.self_hosted_seats_total} seats taken`,
                  },
                  {
                    label: "Waiting line",
                    value: `${c.queue_length ?? "-"} in line`,
                  },
                ]}
              />
            )}
          </AsyncBoundary>
        </Panel>
      </div>

      <Panel
        title="Background tasks"
        description="A task whose worker stopped mid-run is tried once more after three minutes, then marked failed. To retry a failed marking, open the attempt it belongs to."
        actions={
          <B2CSegmentedTabs
            items={JOB_TABS}
            value={status}
            onChange={setStatus}
            compact
            aria-label="Task status"
          />
        }
        padding="none"
      >
        <AsyncBoundary
          state={jobs}
          isEmpty={(page) => page.items.length === 0}
          empty={{
            title: "No tasks",
            description: `Nothing is ${JOB_LABELS[status].toLowerCase()}.`,
            bare: true,
          }}
        >
          {(page) => (
            <RowList flush>
              {page.items.map((job) => (
                <Row key={job.id}>
                  <div className="min-w-0">
                    <p className="text-osce-data font-medium text-ink">
                      #{job.id} · {jobTaskLabel(job.task_name)}
                    </p>
                    <p className="truncate text-osce-meta text-ink-subtle">
                      {[formatDetail(job.args), `${job.attempts} ${job.attempts === 1 ? "run" : "runs"}`]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                    {job.status === "failed" && (job.events ?? []).length > 0 ? (
                      <p className="text-osce-meta text-ink-subtle">
                        {(job.events ?? [])
                          .map((event) => `${JOB_EVENT_LABELS[event.type] ?? humanise(event.type)} ${formatMoment(event.at)}`)
                          .join(" → ")}
                        . The error itself is in the worker log.
                      </p>
                    ) : null}
                  </div>
                  <Badge tone={jobStatusTone(job.status)}>{jobLabel(job.status)}</Badge>
                </Row>
              ))}
            </RowList>
          )}
        </AsyncBoundary>
      </Panel>

      <TutorIndex />
    </div>
  );
}

/** One sentence on overall health, from the same page the panels below read. */
function NowHero({ machinery }: { machinery: Machinery }) {
  const { health, capacity } = machinery;
  const title =
    health.status === "ok"
      ? "Everything is running."
      : health.status === "degraded"
        ? "Something is degraded."
        : "The platform is down.";
  const detail = [
    capacity.active === null
      ? "Voice usage is unknown."
      : `${capacity.active} of ${capacity.max_concurrent} voice sessions held.`,
    capacity.queue_length
      ? `${capacity.queue_length} waiting in line.`
      : null,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <B2CHero eyebrow="Now" title={title}>
      {detail}
    </B2CHero>
  );
}

function TutorIndex() {
  const [reindexing, setReindexing] = useState(false);
  const [reindex, setReindex] = useState<TutorMemoryReindex | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  const run = async () => {
    setReindexing(true);
    setFailure(null);
    try {
      setReindex(await reindexTutorMemory());
    } catch (cause) {
      setFailure(
        errorMessage(cause instanceof Error ? cause : new Error(String(cause))),
      );
    } finally {
      setReindexing(false);
    }
  };

  return (
    <Panel
      title="Tutor material index"
      description="The material the AI tutor can quote from. It updates every night. Update it now if a correction needs to take effect straight away."
      actions={
        <Button
          variant="secondary"
          size="sm"
          isLoading={reindexing}
          onClick={() => run()}
        >
          {reindexing ? "Rebuilding…" : "Rebuild now"}
        </Button>
      }
    >
      {failure ? <Alert tone="danger">{failure}</Alert> : null}
      {reindex ? (
        <Alert tone="success" title="Index rebuilt">
          <p>
            {reindex.sources} sources · {reindex.passages} passages searchable ·{" "}
            {reindex.retired} retired rows removed.
          </p>
        </Alert>
      ) : null}
      {!reindex && !failure ? (
        <p className="text-osce-meta text-ink-subtle">
          Keep this page open until it finishes. A large library can take a few minutes.
        </p>
      ) : null}
    </Panel>
  );
}
