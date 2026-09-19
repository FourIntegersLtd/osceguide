"use client";

import { useCallback, useState } from "react";
import { LuCircleCheck, LuSend } from "react-icons/lu";
import { Alert, AsyncBoundary, Badge, Button, Card, Input, PageHeader, Spinner } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import {
  readSittingReport,
  recordDecision,
  releaseDecision,
  signOffDecision,
  type CandidateReport,
} from "@/domains/assess/api";

const OUTCOMES = ["pass", "fail", "borderline"] as const;

/**
 * The candidates on a sitting, and the workflow that gets a result to them.
 *
 * `draft → signed_off → released`, and the backend holds that order: a draft
 * cannot be released directly and a released decision is final. Sign-off needs
 * an outcome and a rationale, because somebody has to be able to say why.
 */
export function Results({ orgSlug, sittingId }: { orgSlug: string; sittingId: string }) {
  const state = useAsync((signal) => readSittingReport(orgSlug, sittingId, signal), [orgSlug, sittingId]);

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>
        {(report) => (
          <>
            <PageHeader
              title="Results"
              description={`${report.sitting.name} · ${report.totals.stations_marked} of ${report.totals.stations} stations marked`}
              actions={
                <Badge tone="neutral">
                  {report.totals.decisions_released} of {report.totals.candidates} released
                </Badge>
              }
            />
            {(report.candidates ?? []).length === 0 ? (
              <Card>
                <p className="text-sm text-ink-muted">Nobody has sat this yet.</p>
              </Card>
            ) : (
              <ul className="flex flex-col gap-3">
                {(report.candidates ?? []).map((candidate) => (
                  <li key={candidate.user_id}>
                    <CandidateCard
                      orgSlug={orgSlug}
                      sittingId={sittingId}
                      candidate={candidate}
                      onChanged={state.reload}
                    />
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}

function CandidateCard({
  orgSlug,
  sittingId,
  candidate,
  onChanged,
}: {
  orgSlug: string;
  sittingId: string;
  candidate: CandidateReport;
  onChanged: () => void;
}) {
  const [outcome, setOutcome] = useState(candidate.decision?.assessment_outcome ?? "");
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const workflow = candidate.decision?.workflow_state ?? "none";
  const released = Boolean(candidate.decision?.released_at);
  const signedOff = Boolean(candidate.decision?.signed_off_at);
  const traineeId = candidate.trainee_id;

  const run = useCallback(
    async (label: string, action: () => Promise<unknown>) => {
      setBusy(label);
      setError(null);
      try {
        await action();
        onChanged();
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(null);
      }
    },
    [onChanged],
  );

  return (
    <Card
      title={candidate.name ?? candidate.email ?? "Candidate"}
      description={`${candidate.stations_marked} stations marked${candidate.overall_rag ? ` · overall ${candidate.overall_rag}` : ""}`}
      actions={
        released ? (
          <Badge tone="success">Released</Badge>
        ) : signedOff ? (
          <Badge tone="accent">Signed off</Badge>
        ) : (
          <Badge tone="neutral">{workflow}</Badge>
        )
      }
    >
      <div className="flex flex-col gap-3">
        {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
        {!traineeId && (
          <Alert tone="warning">
            This candidate is not a rostered trainee, so a decision cannot be recorded against them.
          </Alert>
        )}

        {traineeId && !released && (
          <>
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex flex-col gap-1.5">
                <span className="text-sm font-medium text-ink">Outcome</span>
                <select
                  value={outcome}
                  onChange={(event) => setOutcome(event.target.value)}
                  className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink"
                >
                  <option value="">Not decided</option>
                  {OUTCOMES.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <Input
                label="Rationale"
                value={rationale}
                onChange={(event) => setRationale(event.target.value)}
                placeholder="Why this outcome"
                className="min-w-[16rem] flex-1"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                disabled={busy !== null || !outcome || !rationale.trim()}
                onClick={() =>
                  run("save", () =>
                    recordDecision(orgSlug, sittingId, traineeId, {
                      assessmentOutcome: outcome,
                      rationale: rationale.trim(),
                    }),
                  )
                }
              >
                {busy === "save" ? <Spinner /> : "Record decision"}
              </Button>
              <Button
                variant="secondary"
                disabled={busy !== null || signedOff}
                onClick={() => run("signoff", () => signOffDecision(orgSlug, sittingId, traineeId))}
              >
                {busy === "signoff" ? <Spinner /> : <LuCircleCheck className="h-4 w-4" aria-hidden />}
                Sign off
              </Button>
              <Button
                disabled={busy !== null || !signedOff}
                onClick={() => run("release", () => releaseDecision(orgSlug, sittingId, traineeId))}
              >
                {busy === "release" ? <Spinner /> : <LuSend className="h-4 w-4" aria-hidden />}
                Release to candidate
              </Button>
            </div>
          </>
        )}

        {released && (
          <p className="text-sm text-ink-muted">
            Released {new Date(candidate.decision!.released_at!).toLocaleString()}. A released
            decision is final; a correction is a new revision.
          </p>
        )}
      </div>
    </Card>
  );
}
