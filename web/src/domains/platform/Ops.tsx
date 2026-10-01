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
import { errorMessage, useAsync, useEventStream } from "@/foundation/hooks";
import {
  machineryStreamPath,
  readMachinery,
  reindexTutorMemory,
  type Machinery,
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
        description="Background tasks, marking, and how many live voice sessions we can run."
        icon={LuActivity}
        actions={
          <Badge tone={stream.connected ? "success" : "warning"}>
            {stream.connected ? "Live" : "Reconnecting"}
          </Badge>
        }
      />

      <div className="grid items-start gap-6 lg:grid-cols-2">
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
        description="To retry a failed marking, open the attempt it belongs to."
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
      description="The material the AI tutor can quote from. It updates every night. Update it now if a correction needs to take effect straight away."
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
          Keep this page open until it finishes. A large library can take a few minutes.
        </p>
      ) : null}
    </Panel>
  );
}
