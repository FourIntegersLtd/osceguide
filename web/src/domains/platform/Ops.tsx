"use client";

import { useState } from "react";
import {
  Alert,
  AsyncBoundary,
  B2CHero,
  Badge,
  Button,
  FactList,
  Panel,
  B2CPageHeader,
} from "@/foundation/ui";
import { errorMessage, useAsync, useEventStream } from "@/foundation/hooks";
import {
  machineryStreamPath,
  readMachinery,
  reindexTutorMemory,
  type Machinery,
  type TutorMemoryReindex,
} from "@/domains/platform/support/api";
import { DatabaseSize } from "@/domains/platform/DatabaseSize";
import { UndeliveredMail } from "@/domains/platform/UndeliveredMail";
import { formatMoment, liveFeedLabel } from "@/domains/platform/support";
import { BackgroundTasks, type JobStatus } from "@/domains/platform/BackgroundTasks";

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
  // When the figures on screen last arrived: the last pushed frame, else the first read.
  const frame = pushed ?? initial.data;
  const [arrival, setArrival] = useState<{ frame: unknown; at: Date } | null>(null);
  // Set while rendering, when a new frame is the first thing that differs: the clock is read once per frame.
  if (frame && arrival?.frame !== frame) setArrival({ frame, at: new Date() });
  const lastFrameAt = arrival?.at ?? null;
  const live = liveFeedLabel(stream.connected, lastFrameAt);
  const machinery = { ...initial, data: pushed ?? initial.data };
  const health = { ...machinery, data: machinery.data?.health ?? null };
  const capacity = { ...machinery, data: machinery.data?.capacity ?? null };
  const jobs = { ...machinery, data: machinery.data?.jobs ?? null };

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="System health"
        subtitle="Pushed live from the platform."
        action={
          <Badge tone={live.tone}>{live.text}</Badge>
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

      <AsyncBoundary state={health}>{(h) => <DatabaseSize size={h.database_size} />}</AsyncBoundary>

      <BackgroundTasks
        status={status}
        onStatus={setStatus}
        jobs={jobs}
        reload={initial.reload}
      />

      <UndeliveredMail />

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
