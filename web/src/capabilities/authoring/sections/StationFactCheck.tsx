"use client";

import { useEffect, useState } from "react";
import { useAsync, useMeEvents } from "@/foundation/hooks";
import { Alert, AsyncBoundary, Panel } from "@/foundation/ui";
import {
  FactCheck,
  corrected,
  factsOf,
  reopened,
  ruled,
  uncorrected,
  type Facts,
} from "@/capabilities/fact-check";
import {
  checkStationFacts,
  readStationReview,
  type AuthoringScope,
} from "@/capabilities/authoring/api";
import { useAction } from "@/capabilities/authoring/parts/useAction";

type Content = Record<string, unknown>;

/**
 * A catalogue station's clinical claims against the guidelines, under its
 * content. A correction edits the content on screen and a ruling is handed up,
 * so "Save content" saves both together, as the media review does.
 */
export function StationFactCheck({
  scope,
  stationId,
  version,
  content,
  onContentChange,
  onRuled,
  editable,
  unsaved,
}: {
  scope: AuthoringScope;
  stationId: string;
  version: number;
  content: Content;
  onContentChange: (content: Content) => void;
  /** The check with the reader's latest ruling on it, for the next save. */
  onRuled: (facts: Facts) => void;
  /** False for a published version: it can be checked but not corrected. */
  editable: boolean;
  /** The check reads what is saved, so it waits while there are edits to save. */
  unsaved: boolean;
}) {
  const load = useAsync(
    (signal) => readStationReview(scope, stationId, version, signal),
    [scope, stationId, version],
  );
  const action = useAction();
  const [facts, setFacts] = useState<Facts | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    if (!load.data) return;
    setFacts(factsOf(load.data.facts));
    setChecking(load.data.checking);
  }, [load.data]);

  useMeEvents(["station.updated"], (event) => {
    if (checking && (event.name === "resync" || event.data.station_id === stationId)) load.reload();
  });

  function rule(next: Facts) {
    setFacts(next);
    onRuled(next);
  }

  return (
    <Panel title="Fact check">
      <AsyncBoundary state={load}>
        {(review) => (
          <div className="flex flex-col gap-4">
            {action.error ? <Alert tone="danger">{action.error}</Alert> : null}
            {review.error && !checking ? (
              <Alert tone="danger">The last fact check failed: {String(review.error.message ?? "")}</Alert>
            ) : null}
            {unsaved && !checking ? (
              <Alert tone="info">Save the content first: the check reads the saved version.</Alert>
            ) : null}
            <FactCheck
              facts={facts}
              locked={unsaved || checking || action.busy !== null}
              working={checking}
              onCheck={() =>
                void action.run("check", async () => {
                  await checkStationFacts(scope, stationId, version);
                  setChecking(true);
                })
              }
              rulings={
                editable && facts
                  ? {
                      onAccept: (claim, swap) => {
                        if (swap) onContentChange(corrected(content, claim, swap));
                        rule(ruled(facts, claim.id, "accepted", swap ?? undefined));
                      },
                      onDismiss: (claim) => rule(ruled(facts, claim.id, "dismissed")),
                      onReopen: (claim) => {
                        onContentChange(uncorrected(content, claim));
                        rule(reopened(facts, claim.id));
                      },
                    }
                  : undefined
              }
            />
          </div>
        )}
      </AsyncBoundary>
    </Panel>
  );
}
