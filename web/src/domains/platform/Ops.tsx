"use client";

import { useState } from "react";
import { LuActivity } from "react-icons/lu";
import {
  Alert,
  AsyncBoundary,
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
import { errorMessage, useAsync } from "@/foundation/hooks";
import {
  listJobs,
  readCloudCapacity,
  readPlatformHealth,
  reindexTutorMemory,
  type TutorMemoryReindex,
} from "@/domains/platform/support/api";
import { formatMoment, jobStatusTone } from "@/domains/platform/support";

type JobStatus = "failed" | "todo" | "doing" | "succeeded";

const JOB_LABELS: Record<JobStatus, string> = {
  failed: "Failed",
  todo: "Waiting",
  doing: "Running",
  succeeded: "Succeeded",
};

const JOB_TABS: B2CSegmentedTabItem<JobStatus>[] = (
  Object.keys(JOB_LABELS) as JobStatus[]
).map((id) => ({ id, label: JOB_LABELS[id] }));

/** Is the platform working, not only up: the queue, the worker, the Cloud cap. */
export function Ops() {
  const health = useAsync((signal) => readPlatformHealth(signal), []);
  const capacity = useAsync((signal) => readCloudCapacity(signal), []);
  const [status, setStatus] = useState<JobStatus>("failed");
  const jobs = useAsync(
    (signal) => listJobs({ status, limit: 100 }, signal),
    [status],
  );

  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="Machinery"
        description="The queue, the worker, and LiveKit Cloud."
        icon={LuActivity}
      />

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <Panel title="Platform">
          <AsyncBoundary state={health}>
            {(h) => (
              <FactList
                items={[
                  { label: "Status", value: `${h.status} · v${h.version}` },
                  {
                    label: "Worker last seen",
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
                    label: "Queue",
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
                    label: "LiveKit Cloud",
                    value:
                      c.active === null
                        ? "Unknown — new sessions go self-hosted"
                        : `${c.active} of ${c.max_concurrent} held · ${c.free} free`,
                  },
                  {
                    label: "Overflow metering",
                    value: c.overflow_enabled ? "On" : "Off",
                  },
                  {
                    label: "Our workers",
                    value: `${c.self_hosted_seats_taken ?? "—"} of ${c.self_hosted_seats_total} seats taken`,
                  },
                  {
                    label: "Waiting line",
                    value: `${c.queue_length ?? "—"} in line`,
                  },
                ]}
              />
            )}
          </AsyncBoundary>
        </Panel>
      </div>

      <Panel
        title="Jobs"
        description="No retry here: a failed marking is re-queued from the attempt it was about."
        actions={
          <B2CSegmentedTabs
            items={JOB_TABS}
            value={status}
            onChange={setStatus}
            compact
            aria-label="Job status"
          />
        }
        padding="none"
      >
        <AsyncBoundary
          state={jobs}
          isEmpty={(page) => page.items.length === 0}
          empty={{
            title: "No jobs",
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
                      #{job.id} · {job.task_name}
                    </p>
                    <p className="truncate text-osce-meta text-ink-subtle">
                      {Object.entries(job.args)
                        .map(([key, value]) => `${key}=${String(value)}`)
                        .join(" · ")}{" "}
                      · {job.attempts} runs
                    </p>
                  </div>
                  <Badge tone={jobStatusTone(job.status)}>{job.status}</Badge>
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
      description="What the tutor may quote. It rebuilds nightly; rebuild now when a correction has to be true straight away."
      actions={
        <Button
          variant="secondary"
          size="sm"
          isLoading={reindexing}
          onClick={() => void run()}
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
          Runs to completion in the browser rather than returning a job to poll,
          so a large library takes a while here on purpose.
        </p>
      ) : null}
    </Panel>
  );
}
