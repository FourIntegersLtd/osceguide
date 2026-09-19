"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { LuArrowLeft } from "react-icons/lu";
import { Alert, AsyncBoundary, Badge, Card } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { kindLabel } from "@/capabilities/transcripts/api";
import { readTranscript, TranscriptView } from "@/capabilities/feedback";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import {
  failAttempt,
  readAttemptForSupport,
  rescoreAttempt,
  salvageAttempt,
  type PlatformAttemptDetail,
} from "@/domains/platform/support/api";
import { Row, RowList, Section } from "@/domains/platform/chrome";
import { InlineAction } from "@/domains/platform/user/InlineAction";
import {
  attemptStatusLabel,
  attemptStatusTone,
  diagnoseAttempt,
  formatMoment,
  jobStatusTone,
} from "@/domains/platform/support";

/**
 * One attempt, from the outside: what the console needs to say why there is
 * no feedback, and the three things it can do about it.
 *
 * The candidate's own reads — transcript, result — already admit a platform
 * admin by id; what they cannot say is whether the marking was ever queued,
 * or failed, or whether the worker ever fetched the attempt at all. This is
 * `GET /platform/attempts/{id}`, which does.
 */
export function AttemptInspector({ attemptId }: { attemptId: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => readAttemptForSupport(attemptId, signal), [attemptId]);
  const [fresh, setFresh] = useState<PlatformAttemptDetail | null>(null);

  return (
    <div className="flex flex-col gap-8">
      <AsyncBoundary state={state}>
        {(loaded) => {
          const attempt = fresh ?? loaded;
          const diagnosis = diagnoseAttempt(attempt);
          return (
            <>
              <div>
                <Link
                  href={`${hrefFor(`/users/${encodeURIComponent(attempt.user_id)}`)}`}
                  className="inline-flex items-center gap-1.5 text-sm text-ink-muted transition-colors hover:text-ink"
                >
                  <LuArrowLeft className="h-4 w-4" aria-hidden /> Back to the account
                </Link>
              </div>
              <PlatformPageHeader
                title={`${kindLabel(attempt.kind)} · ${formatMoment(attempt.created_at)}`}
                description={`${attempt.id}${attempt.room_name ? ` · room ${attempt.room_name}` : ""}`}
                actions={<Badge tone={attemptStatusTone(attempt.status)}>{attemptStatusLabel(attempt.status)}</Badge>}
              />

              <Section title="What happened">
                <Card padding="md">
                  <dl className="grid gap-2 text-sm sm:grid-cols-2">
                    <Fact label="Definition frozen" value={attempt.has_definition ? formatMoment(attempt.definition_frozen_at) : "Never — the worker did not fetch it"} />
                    <Fact label="Turns received" value={String(attempt.chunk_count)} />
                    <Fact label="Transcript delivered" value={attempt.transcript_complete ? formatMoment(attempt.transcript_delivered_at) : "Not delivered"} />
                    <Fact label="Marked under" value={attempt.result_policy_versions.length ? attempt.result_policy_versions.join(", ") : "Nothing yet"} />
                    <Fact label="Started" value={formatMoment(attempt.started_at)} />
                    <Fact label="Finished" value={formatMoment(attempt.completed_at)} />
                    {attempt.failed_reason ? <Fact label="Failed because" value={attempt.failed_reason} /> : null}
                  </dl>
                  {diagnosis ? (
                    <div className="mt-4">
                      <Alert tone="warning">{diagnosis.problem}</Alert>
                    </div>
                  ) : null}
                </Card>
              </Section>

              <Actions attempt={attempt} suggested={diagnosis?.action ?? null} onChanged={setFresh} />

              <Section title="Marking jobs" description="Every job the queue has held for this attempt, newest first.">
                {attempt.jobs.length === 0 ? (
                  <Card padding="md">
                    <p className="text-sm text-ink-muted">Nothing was ever queued.</p>
                  </Card>
                ) : (
                  <RowList>
                    {attempt.jobs.map((job) => (
                      <Row key={job.id}>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-ink">
                            #{job.id} · {job.policy_version ?? "default policy"}
                          </p>
                          <p className="text-xs text-ink-subtle">
                            {job.attempts} run{job.attempts === 1 ? "" : "s"}
                            {job.scheduled_at ? ` · scheduled ${formatMoment(job.scheduled_at)}` : ""}
                          </p>
                        </div>
                        <Badge tone={jobStatusTone(job.status)}>{job.status}</Badge>
                      </Row>
                    ))}
                  </RowList>
                )}
              </Section>

              <TranscriptSection attemptId={attempt.id} available={attempt.chunk_count > 0} />
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs uppercase tracking-wide text-ink-subtle">{label}</dt>
      <dd className="truncate text-ink">{value}</dd>
    </div>
  );
}

function Actions({
  attempt,
  suggested,
  onChanged,
}: {
  attempt: PlatformAttemptDetail;
  suggested: "salvage" | "rescore" | "fail" | null;
  onChanged: (attempt: PlatformAttemptDetail) => void;
}) {
  const toast = useToast();
  const terminal = attempt.status === "evaluated" || attempt.status === "failed";
  const markable = attempt.status === "interaction_complete" || attempt.status === "evaluated";
  const [policy, setPolicy] = useState("");

  const reload = useCallback(async () => onChanged(await readAttemptForSupport(attempt.id)), [attempt.id, onChanged]);

  return (
    <Section title="Fix it" description={suggested ? `Suggested: ${suggested}.` : "Nothing needs doing."}>
      <Card padding="md">
        <div className="flex flex-wrap gap-2">
          {markable ? (
            <InlineAction
              label="Re-queue the marking"
              requireReason={false}
              reasonLabel="Policy version (optional)"
              description="Twice is once: a marking already waiting is left waiting, and a result already written is kept. Name a different policy version to mark again beside the old result."
              onConfirm={async (version) => {
                const result = await rescoreAttempt(attempt.id, version || policy || null);
                toast.success(result.queued ? "Marking queued" : `Not queued: ${result.reason?.replace(/_/g, " ")}`);
                setPolicy("");
                await reload();
              }}
            />
          ) : null}
          {attempt.status === "running" ? (
            <InlineAction
              label="Salvage the transcript"
              requireReason={false}
              reasonLabel="Note (optional)"
              description="Treats the turns that arrived as the transcript the worker never delivered, and queues the marking."
              onConfirm={async () => {
                onChanged(await salvageAttempt(attempt.id));
                toast.success("Transcript salvaged", "The marking has been queued.");
              }}
            />
          ) : null}
          {!terminal ? (
            <InlineAction
              label="Fail this attempt"
              tone="danger"
              description="Ends it so a fresh attempt can start. The recording, such as it is, stays."
              onConfirm={async (reason) => {
                onChanged(await failAttempt(attempt.id, reason));
                toast.success("Attempt failed", "They can start again.");
              }}
            />
          ) : null}
          {terminal && !markable ? <p className="text-sm text-ink-muted">A failed attempt is final; start a fresh one.</p> : null}
        </div>
      </Card>
    </Section>
  );
}

function TranscriptSection({ attemptId, available }: { attemptId: string; available: boolean }) {
  const state = useAsync(
    async (signal) => (available ? readTranscript(attemptId, signal) : null),
    [attemptId, available],
  );
  return (
    <Section title="Transcript" description="What was said, in order — the turns that reached us.">
      {!available ? (
        <Card padding="md">
          <p className="text-sm text-ink-muted">No turns were received.</p>
        </Card>
      ) : (
        <Card padding="md">
          <AsyncBoundary state={state}>
            {(transcript) => (transcript ? <TranscriptView transcript={transcript} /> : <p className="text-sm text-ink-muted">{errorMessage(new Error("No transcript"))}</p>)}
          </AsyncBoundary>
        </Card>
      )}
    </Section>
  );
}
