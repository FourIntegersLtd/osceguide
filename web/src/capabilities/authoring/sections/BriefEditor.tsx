"use client";

import { useState } from "react";
import { Alert, Button, Card } from "@/foundation/ui";
import { editStationBrief, type StationVersion } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";

/**
 * The reading brief, editable without cutting a new version.
 *
 * Mounted with the version as its key, so switching version remounts it with
 * that version's text rather than synchronising two sources of truth in an
 * effect.
 *
 * The brief is what a candidate is handed before the station starts —
 * presentation, not assessed content — so correcting a typo in one does not
 * invalidate what everybody else was marked against. That is why it has its
 * own endpoint and its own box here rather than living in the content editor.
 */
export function BriefEditor({
  stationId,
  version,
  initial,
  onSaved,
}: {
  stationId: string;
  version: number;
  initial: string;
  onSaved: (version: StationVersion) => void;
}) {
  const scope = useAuthoringScope();
  const [brief, setBrief] = useState(initial);
  const [saved, setSaved] = useState(false);
  const action = useAction();

  return (
    <Card themeType="b2b" padding="md">
      <h3 className="text-osce-body font-semibold text-b2b-headline">Reading brief</h3>
      <p className="mt-0.5 text-osce-caption text-b2b-mid">
        What the candidate reads before the station starts. Saving this does not cut a new version.
      </p>
      <textarea
        value={brief}
        rows={8}
        onChange={(e) => {
          setBrief(e.target.value);
          setSaved(false);
        }}
        className="mt-3 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline focus:border-osce-accent focus:outline-none focus:ring-2 focus:ring-osce-accent-subtle"
      />
      {action.error ? (
        <Alert tone="danger" className="mt-3">
          {action.error}
        </Alert>
      ) : null}
      <div className="mt-3 flex items-center gap-3">
        <Button
          themeType="b2b"
          variant="commit"
          size="sm"
          disabled={action.busy !== null || brief === initial}
          onClick={() =>
            void action.run("brief", async () => {
              onSaved(await editStationBrief(scope, stationId, version, brief));
              setSaved(true);
            })
          }
        >
          {action.busy === "brief" ? "Saving…" : "Save brief"}
        </Button>
        {saved ? <span className="text-osce-caption text-b2b-success-text">Saved.</span> : null}
      </div>
    </Card>
  );
}
