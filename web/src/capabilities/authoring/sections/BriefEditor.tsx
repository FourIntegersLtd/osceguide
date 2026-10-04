"use client";

import { useState } from "react";
import { Alert, Textarea, Panel } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
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
    <Panel
      title="Reading brief"
      description="What the candidate reads before the station starts. Saving this does not cut a new version."
    >
      <Textarea
        value={brief}
        rows={8}
        onChange={(e) => {
          setBrief(e.target.value);
          setSaved(false);
        }}
      />
      {action.error ? (
        <Alert tone="danger" className="mt-3">
          {action.error}
        </Alert>
      ) : null}
      <div className="mt-3 flex items-center gap-3">
        <AuthoringButton
          variant="commit"
          size="sm"
          disabled={action.busy !== null || brief === initial}
          onClick={() =>
            action.run("brief", async () => {
              onSaved(await editStationBrief(scope, stationId, version, brief));
              setSaved(true);
            })
          }
        >
          {action.busy === "brief" ? "Saving…" : "Save brief"}
        </AuthoringButton>
        {saved ? <span className="text-osce-caption text-osce-success-text">Saved.</span> : null}
      </div>
    </Panel>
  );
}
