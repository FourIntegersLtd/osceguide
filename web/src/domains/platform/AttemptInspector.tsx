"use client";

import { useCallback, useState } from "react";
import {
  ActionRail,
  Alert,
  AsyncBoundary,
  Badge,
  DetailLayout,
  EmptyPanel,
  FactList,
  Panel,
  PlatformPageHeader,
  Row,
  RowList,
} from "@/foundation/ui";
import { useAsync, useToast } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { kindLabel } from "@/capabilities/transcripts/api";
import {
  AttemptFeedback,
  readTranscript,
  TranscriptView,
} from "@/capabilities/feedback";
import {
  failAttempt,
  readAttemptForSupport,
  rescoreAttempt,
  salvageAttempt,
  type PlatformAttemptDetail,
} from "@/domains/platform/support/api";
import { InlineAction } from "@/domains/platform/user/InlineAction";
import {
  attemptStatusLabel,
  attemptStatusTone,
  diagnoseAttempt,
  formatMoment,
  jobStatusTone,
} from "@/domains/platform/support";

/**
 * One attempt, from the outside: why there is no feedback, and the three
 * things the console can do about it.
 *
 * The candidate's own reads — transcript, result — already admit a platform
 * admin by id; what they cannot say is whether the marking was ever queued,
 * or failed, or whether the worker ever fetched the attempt at all. This is
 * `GET /platform/attempts/{id}`, which does.
 */
export function AttemptInspector({ attemptId }: { attemptId: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync(
    (signal) => readAttemptForSupport(attemptId, signal),
    [attemptId],
  );
  const [fresh, setFresh] = useState<PlatformAttemptDetail | null>(null);

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>
        {(loaded) => {
          const attempt = fresh ?? loaded;
          const diagnosis = diagnoseAttempt(attempt);
          return (
            <>
              <PlatformPageHeader
                title={`${kindLabel(attempt.kind)} · ${formatMoment(attempt.created_at)}`}
                description={`${attempt.id}${attempt.room_name ? ` · room ${attempt.room_name}` : ""}`}
                back={{
                  href: hrefFor(
                    `/users/${encodeURIComponent(attempt.user_id)}`,
                  ),
                  label: "Account",
                }}
                actions={
                  <Badge tone={attemptStatusTone(attempt.status)}>
                    {attemptStatusLabel(attempt.status)}
                  </Badge>
                }
              />

              <DetailLayout
                main={
                  <>
                    <Panel title="What happened">
                      <div className="flex flex-col gap-5">
                        {diagnosis ? (
                          <Alert tone="warning">{diagnosis.problem}</Alert>
                        ) : null}
                        <FactList items={attemptFacts(attempt)} />
                      </div>
                    </Panel>

                    <Panel
                      title="Marking jobs"
                      description="Every job the queue has held for this attempt, newest first."
                      padding="none"
                    >
                      {attempt.jobs.length === 0 ? (
                        <EmptyPanel bare title="Nothing was ever queued" />
                      ) : (
                        <RowList flush>
                          {attempt.jobs.map((job) => (
                            <Row key={job.id}>
                              <div className="min-w-0">
                                <p className="text-osce-data font-medium text-ink">
                                  #{job.id} ·{" "}
                                  {job.policy_version ?? "default policy"}
                                </p>
                                <p className="text-osce-meta text-ink-subtle">
                                  {job.attempts} run
                                  {job.attempts === 1 ? "" : "s"}
                                  {job.scheduled_at
                                    ? ` · scheduled ${formatMoment(job.scheduled_at)}`
                                    : ""}
                                </p>
                              </div>
                              <Badge tone={jobStatusTone(job.status)}>
                                {job.status}
                              </Badge>
                            </Row>
                          ))}
                        </RowList>
                      )}
                    </Panel>

                    {/* What the candidate reads, drawn from the same rubric, so support
                        can see the feedback a complaint is about rather than infer it. */}
                    {attempt.result_policy_versions.length > 0 ? (
                      <Panel
                        title="Feedback"
                        description="The marking as the candidate sees it."
                      >
                        <AttemptFeedback attemptId={attempt.id} />
                      </Panel>
                    ) : null}

                    <TranscriptSection
                      attemptId={attempt.id}
                      available={attempt.chunk_count > 0}
                    />
                  </>
                }
                rail={
                  <Actions
                    attempt={attempt}
                    suggested={diagnosis?.action ?? null}
                    onChanged={setFresh}
                  />
                }
              />
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

function attemptFacts(
  attempt: PlatformAttemptDetail,
): { label: string; value: string }[] {
  const facts = [
    {
      label: "Definition frozen",
      value: attempt.has_definition
        ? formatMoment(attempt.definition_frozen_at)
        : "Never — the worker did not fetch it",
    },
    { label: "Turns received", value: String(attempt.chunk_count) },
    {
      label: "Transcript delivered",
      value: attempt.transcript_complete
        ? formatMoment(attempt.transcript_delivered_at)
        : "Not delivered",
    },
    {
      label: "Marked under",
      value: attempt.result_policy_versions.length
        ? attempt.result_policy_versions.join(", ")
        : "Nothing yet",
    },
    { label: "Started", value: formatMoment(attempt.started_at) },
    { label: "Finished", value: formatMoment(attempt.completed_at) },
  ];
  if (attempt.failed_reason)
    facts.push({ label: "Failed because", value: attempt.failed_reason });
  return facts;
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
  const terminal =
    attempt.status === "evaluated" || attempt.status === "failed";
  const markable =
    attempt.status === "interaction_complete" || attempt.status === "evaluated";

  const reload = useCallback(
    async () => onChanged(await readAttemptForSupport(attempt.id)),
    [attempt.id, onChanged],
  );

  return (
    <ActionRail
      title="Fix it"
      danger={
        !terminal ? (
          <InlineAction
            label="Fail this attempt"
            tone="danger"
            description="Ends it so a fresh attempt can start. The recording, such as it is, stays."
            onConfirm={async (reason) => {
              onChanged(await failAttempt(attempt.id, reason));
              toast.success("Attempt failed", "They can start again.");
            }}
          />
        ) : undefined
      }
    >
      <p className="text-osce-meta text-ink-subtle">
        {suggested ? `Suggested: ${suggested}.` : "Nothing needs doing."}
      </p>
      {markable ? (
        <InlineAction
          label="Re-queue the marking"
          requireReason={false}
          reasonLabel="Policy version (optional)"
          description="Twice is once: a marking already waiting is left waiting, and a result already written is kept. Name a different policy version to mark again beside the old result."
          onConfirm={async (version) => {
            const result = await rescoreAttempt(attempt.id, version || null);
            toast.success(
              result.queued
                ? "Marking queued"
                : `Not queued: ${result.reason?.replace(/_/g, " ")}`,
            );
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
            toast.success(
              "Transcript salvaged",
              "The marking has been queued.",
            );
          }}
        />
      ) : null}
      {terminal && !markable ? (
        <p className="text-osce-meta text-ink-subtle">
          A failed attempt is final; start a fresh one.
        </p>
      ) : null}
    </ActionRail>
  );
}

function TranscriptSection({
  attemptId,
  available,
}: {
  attemptId: string;
  available: boolean;
}) {
  const state = useAsync(
    async (signal) => (available ? readTranscript(attemptId, signal) : null),
    [attemptId, available],
  );
  return (
    <Panel
      title="Transcript"
      description="What was said, in order — the turns that reached us."
    >
      {!available ? (
        <EmptyPanel bare title="No turns were received" />
      ) : (
        <AsyncBoundary
          state={state}
          empty={{ title: "No transcript", bare: true }}
        >
          {(transcript) =>
            transcript ? <TranscriptView transcript={transcript} /> : null
          }
        </AsyncBoundary>
      )}
    </Panel>
  );
}
