"use client";

import { useCallback, useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, Card, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { acknowledgeResult, readMyResult } from "@/domains/assess/api";

/**
 * A candidate's own result, once it has been released and not before.
 *
 * What is shown is the server's projection. The disclosure policy is not
 * reproduced here: a frontend that decides what a candidate may see is a
 * frontend that can be wrong about it.
 */
export function MyResult({ sittingId }: { sittingId: string }) {
  const state = useAsync((signal) => readMyResult(sittingId, signal), [sittingId]);
  const [acknowledging, setAcknowledging] = useState(false);

  const acknowledge = useCallback(async () => {
    setAcknowledging(true);
    try {
      await acknowledgeResult(sittingId);
      state.reload();
    } finally {
      setAcknowledging(false);
    }
  }, [sittingId, state]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Your result" />
      <AsyncBoundary state={state}>
        {(result) =>
          result.released_at === null ? (
            <Card>
              <p className="text-sm text-ink-muted">
                Your result has not been released yet. You will be told when it is.
              </p>
            </Card>
          ) : (
            <Card
              title="Outcome"
              actions={
                <Badge tone={result.assessment_outcome === "pass" ? "success" : "neutral"}>
                  {result.assessment_outcome ?? "recorded"}
                </Badge>
              }
            >
              <div className="flex flex-col gap-4">
                {result.rationale && (
                  <p className="whitespace-pre-wrap text-sm text-ink-muted">{result.rationale}</p>
                )}
                <p className="text-xs text-ink-subtle">
                  Released {new Date(result.released_at).toLocaleString()}
                </p>
                {result.acknowledged_at ? (
                  <Alert tone="success">
                    You acknowledged this on {new Date(result.acknowledged_at).toLocaleDateString()}.
                  </Alert>
                ) : (
                  <div>
                    <Button onClick={acknowledge} disabled={acknowledging}>
                      I have read this
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          )
        }
      </AsyncBoundary>
    </div>
  );
}
