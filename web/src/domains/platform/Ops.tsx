"use client";

import { useState } from "react";
import { LuActivity } from "react-icons/lu";
import { Alert, AsyncBoundary, Badge, Button, Card } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import {
  listJobs,
  readCloudCapacity,
  readPlatformHealth,
  reindexTutorMemory,
  type TutorMemoryReindex,
} from "@/domains/platform/support/api";
import { Row, RowList, Section } from "@/domains/platform/chrome";
import { formatMoment, jobStatusTone } from "@/domains/platform/support";

const JOB_STATUSES = ["failed", "todo", "doing", "succeeded"] as const;

/** Is the platform working, not only up: the queue, the worker, the Cloud cap. */
export function Ops() {
  const health = useAsync((signal) => readPlatformHealth(signal), []);
  const capacity = useAsync((signal) => readCloudCapacity(signal), []);
  const [status, setStatus] = useState<string>("failed");
  const jobs = useAsync((signal) => listJobs({ status, limit: 100 }, signal), [status]);
  const [reindexing, setReindexing] = useState(false);
  const [reindex, setReindex] = useState<TutorMemoryReindex | null>(null);
  const [reindexFailure, setReindexFailure] = useState<string | null>(null);

  const runReindex = async () => {
    setReindexing(true);
    setReindexFailure(null);
    try {
      setReindex(await reindexTutorMemory());
    } catch (cause) {
      setReindexFailure(errorMessage(cause instanceof Error ? cause : new Error(String(cause))));
    } finally {
      setReindexing(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <PlatformPageHeader title="Machinery" description="The queue, the worker, and LiveKit Cloud." icon={LuActivity} />
      <div className="grid gap-3 sm:grid-cols-2">
        <Card padding="md">
          <AsyncBoundary state={health}>
            {(h) => (
              <div className="text-sm">
                <p className="font-medium text-ink">Platform {h.status} · v{h.version}</p>
                <p className="text-ink-muted">
                  {Object.entries(h.checks).map(([k, v]) => `${k} ${v}`).join(" · ")}
                </p>
                <p className="text-ink-muted">
                  Worker last seen {h.worker_seen_at ? formatMoment(h.worker_seen_at) : "never"}
                </p>
                <p className="text-ink-muted">
                  Queue: {Object.entries(h.jobs_by_status).filter(([, n]) => n > 0).map(([k, n]) => `${k} ${n}`).join(" · ") || "empty"}
                </p>
              </div>
            )}
          </AsyncBoundary>
        </Card>
        <Card padding="md">
          <AsyncBoundary state={capacity}>
            {(c) => (
              <div className="text-sm">
                <p className="font-medium text-ink">LiveKit Cloud</p>
                <p className="text-ink-muted">
                  {c.active === null
                    ? "Redis could not say — new sessions go self-hosted."
                    : `${c.active} of ${c.max_concurrent} slots held, ${c.free} free`}
                  {c.overflow_enabled ? "" : " · overflow metering off"}
                </p>
              </div>
            )}
          </AsyncBoundary>
        </Card>
      </div>
      <Section
        title="The tutor's material index"
        description="What the tutor has been told it may quote. It rebuilds nightly; this is for the moment somebody publishes a correction and wants it to be true now."
        actions={
          <Button variant="secondary" size="sm" isLoading={reindexing} onClick={() => void runReindex()}>
            {reindexing ? "Rebuilding…" : "Rebuild now"}
          </Button>
        }
      >
        {reindexFailure ? <Alert tone="danger">{reindexFailure}</Alert> : null}
        {reindex ? (
          <Alert tone="success" title="Index rebuilt">
            <p>
              {reindex.sources} sources · {reindex.passages} passages searchable ·{" "}
              {reindex.retired} retired rows removed.
            </p>
          </Alert>
        ) : null}
        {!reindex && !reindexFailure ? (
          <p className="text-sm text-ink-muted">
            The request runs to completion in the browser rather than returning a job to poll, so a
            large library takes a while here on purpose.
          </p>
        ) : null}
      </Section>
      <Section
        title="Jobs"
        description="No retry here: a failed marking is re-queued from the attempt it was about."
        actions={JOB_STATUSES.map((s) => (
          <Button key={s} variant={status === s ? "primary" : "secondary"} size="sm" onClick={() => setStatus(s)}>
            {s}
          </Button>
        ))}
      >
        <AsyncBoundary state={jobs} isEmpty={(p) => p.items.length === 0} empty={{ title: "No jobs", description: `Nothing is ${status}.` }}>
          {(page) => (
            <RowList>
              {page.items.map((job) => (
                <Row key={job.id}>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-ink">#{job.id} · {job.task_name}</p>
                    <p className="truncate text-xs text-ink-subtle">
                      {Object.entries(job.args).map(([k, v]) => `${k}=${String(v)}`).join(" · ")} · {job.attempts} runs
                    </p>
                  </div>
                  <Badge tone={jobStatusTone(job.status)}>{job.status}</Badge>
                </Row>
              ))}
            </RowList>
          )}
        </AsyncBoundary>
      </Section>
    </div>
  );
}
