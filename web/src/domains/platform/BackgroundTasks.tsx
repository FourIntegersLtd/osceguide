"use client";

import { useState } from "react";
import Table from "@/foundation/table/Table";
import { humanise } from "@/foundation/format";
import {
  Alert,
  AsyncBoundary,
  B2CSegmentedTabs,
  Badge,
  Button,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { errorMessage, type AsyncState } from "@/foundation/hooks";
import {
  cancelJob,
  listJobs,
  retryJob,
  type Job,
  type Machinery,
} from "@/domains/platform/support/api";
import {
  formatDetail,
  formatMoment,
  jobRunningLabel,
  jobStatusTone,
  jobTaskLabel,
  mergeOlderJobs,
} from "@/domains/platform/support";

/** The scoring task: retried from its attempt, never replayed blind from here. */
const SCORING_TASK = "score_attempt";

export type JobStatus = "failed" | "todo" | "doing" | "succeeded";

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
 * The queue on System health: one tab per status, a retry for a failed task,
 * a cancel for a waiting or stalled one, and older pages on request.
 */
export function BackgroundTasks({
  status,
  onStatus,
  jobs,
  reload,
}: {
  status: JobStatus;
  onStatus: (status: JobStatus) => void;
  jobs: AsyncState<Machinery["jobs"] | null>;
  reload: () => void;
}) {
  const [older, setOlder] = useState<{ status: JobStatus; items: Job[]; next: number | null } | null>(null);
  const [jobWorking, setJobWorking] = useState<number | null>(null);
  const [jobFailure, setJobFailure] = useState<string | null>(null);
  // Older pages belong to the tab they were fetched on.
  const olderHere = older?.status === status ? older : null;
  const nextBeforeId = olderHere ? olderHere.next : (jobs.data?.next_before_id ?? null);

  const showOlder = async () => {
    if (nextBeforeId === null) return;
    setJobWorking(-1);
    setJobFailure(null);
    try {
      const page = await listJobs(status, nextBeforeId);
      setOlder({
        status,
        items: mergeOlderJobs(olderHere?.items ?? [], page.items),
        next: page.next_before_id,
      });
    } catch (cause) {
      setJobFailure(errorMessage(cause));
    } finally {
      setJobWorking(null);
    }
  };

  const actOnJob = async (job: Job, act: (id: number) => Promise<void>) => {
    setJobWorking(job.id);
    setJobFailure(null);
    try {
      await act(job.id);
      reload();
    } catch (cause) {
      setJobFailure(errorMessage(cause));
    } finally {
      setJobWorking(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <B2CSegmentedTabs
        items={JOB_TABS}
        value={status}
        onChange={onStatus}
        compact
        aria-label="Task status"
      />
      {jobFailure ? <Alert tone="danger">{jobFailure}</Alert> : null}
      <AsyncBoundary state={jobs}>
        {(page) => (
          <Table<Job>
            rows={mergeOlderJobs(page.items, olderHere?.items ?? [])}
            themeType="b2b"
            idField="id"
            title="Background tasks"
            description="A task whose worker stopped mid-run is tried once more after three minutes, then marked failed. Retry a failed task here; to retry a failed marking, open the attempt it belongs to."
            empty={{
              title: "No tasks",
              description: `Nothing is ${JOB_LABELS[status].toLowerCase()}.`,
            }}
            more={{
              hasMore: nextBeforeId !== null,
              loadingMore: jobWorking === -1,
              moreError: null,
              loadMore: () => void showOlder(),
            }}
            columns={[
              {
                header: "Task",
                key: "task_name",
                priority: "primary",
                render: (job) => {
                  const running = jobRunningLabel(job, new Date());
                  return (
                    <div className="min-w-0">
                      <p className="font-medium text-ink">
                        #{job.id} · {jobTaskLabel(job.task_name)}
                      </p>
                      <p className="truncate text-osce-meta text-ink-subtle">
                        {[
                          formatDetail(job.args),
                          `${job.attempts} ${job.attempts === 1 ? "run" : "runs"}`,
                          running?.text,
                        ]
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
                  );
                },
              },
              {
                header: "Status",
                key: "status",
                render: (job) => (
                  <Badge tone={jobStatusTone(job.status)} dot>
                    {jobLabel(job.status)}
                  </Badge>
                ),
              },
              {
                header: "",
                key: "id",
                render: (job) => {
                  const running = jobRunningLabel(job, new Date());
                  return (
                    <div className="flex items-center gap-2">
                      {job.status === "failed" && job.task_name !== SCORING_TASK ? (
                        <Button
                          themeType="b2b"
                          variant="secondary"
                          size="sm"
                          isLoading={jobWorking === job.id}
                          disabled={jobWorking !== null}
                          onClick={() => actOnJob(job, retryJob)}
                        >
                          Retry
                        </Button>
                      ) : null}
                      {job.status === "todo" || (running?.cancellable ?? false) ? (
                        <Button
                          themeType="b2b"
                          variant="secondary"
                          size="sm"
                          isLoading={jobWorking === job.id}
                          disabled={jobWorking !== null}
                          onClick={() => actOnJob(job, cancelJob)}
                        >
                          Cancel
                        </Button>
                      ) : null}
                    </div>
                  );
                },
              },
            ]}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}
