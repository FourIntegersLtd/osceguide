"use client";

import { useEffect, useRef, useState } from "react";
import { useAsync, useMeEvents } from "@/foundation/hooks";
import { Alert, AsyncBoundary, Panel } from "@/foundation/ui";
import {
  ERROR_STEPS,
  FactCheck,
  ProduceForm,
  RunLog,
  briefOf,
  corrected,
  factsOf,
  reopened,
  ruled,
  runOf,
  uncorrected,
  type Facts,
} from "@/capabilities/fact-check";
import {
  checkStationFacts,
  produceStation,
  readStationReview,
  stopProducingStation,
  type AuthoringScope,
} from "@/capabilities/authoring/api";
import { useAction } from "@/capabilities/authoring/parts/useAction";

type Content = Record<string, unknown>;

/**
 * A catalogue station's clinical claims against the guidelines, under its
 * content. A correction edits the content on screen and a ruling is handed up,
 * so "Save content" saves both together, as the media review does. The agent
 * can draft a draft version from a brief, check it and correct it; its run is
 * shown here and the content is read again when it ends.
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
  onProduced,
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
  /** The agent has stopped working on the version, so its saved content has changed. */
  onProduced: () => void;
}) {
  const load = useAsync(
    (signal) => readStationReview(scope, stationId, version, signal),
    [scope, stationId, version],
  );
  const action = useAction();
  const [facts, setFacts] = useState<Facts | null>(null);
  const [checking, setChecking] = useState(false);
  const [producing, setProducing] = useState(false);
  const wasProducing = useRef(false);

  useEffect(() => {
    if (!load.data) return;
    setFacts(factsOf(load.data.facts));
    setChecking(load.data.checking);
    if (wasProducing.current && !load.data.producing) onProduced();
    wasProducing.current = load.data.producing;
    setProducing(load.data.producing);
  }, [load.data, onProduced]);

  useMeEvents(["station.updated"], (event) => {
    if ((checking || producing) && (event.name === "resync" || event.data.station_id === stationId))
      load.reload();
  });

  function rule(next: Facts) {
    setFacts(next);
    onRuled(next);
  }

  return (
    <Panel title="Fact check">
      <AsyncBoundary state={load}>
        {(review) => {
          const run = runOf(review.run);
          const busy = checking || producing;
          return (
          <div className="flex flex-col gap-4">
            {action.error ? <Alert tone="danger">{action.error}</Alert> : null}
            {review.error && !busy ? (
              <Alert tone="danger">
                The last {ERROR_STEPS[String(review.error.step)] ?? "fact check"} failed:{" "}
                {String(review.error.message ?? "")}
              </Alert>
            ) : null}
            {unsaved && !busy ? (
              <Alert tone="info">Save the content first: the check reads the saved version.</Alert>
            ) : null}
            {run ? (
              <RunLog
                run={run}
                running={producing}
                stopping={action.busy === "stop"}
                onStop={() =>
                  void action.run("stop", async () => {
                    await stopProducingStation(scope, stationId, version);
                    load.reload();
                  })
                }
              />
            ) : null}
            {editable ? (
              <ProduceForm
                key={briefOf(review.brief)?.brief ?? ""}
                brief={briefOf(review.brief)}
                hint="What the station tests and for which exam. With nothing written the agent drafts it; then it checks the facts and corrects what the sources contradict, listing what it changed."
                locked={unsaved || busy || action.busy !== null}
                working={producing}
                onProduce={(brief) =>
                  void action.run("produce", async () => {
                    await produceStation(scope, stationId, version, { brief });
                    setProducing(true);
                    load.reload();
                  })
                }
              />
            ) : null}
            <FactCheck
              facts={facts}
              locked={unsaved || busy || action.busy !== null}
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
          );
        }}
      </AsyncBoundary>
    </Panel>
  );
}
