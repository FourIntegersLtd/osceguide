"use client";

import { useState } from "react";
import { Alert, Textarea, Panel } from "@/foundation/ui";
import { boardBtn, boardInput, boardPad } from "@/foundation/ui/boardKit";
import { boardMeta } from "@/capabilities/authoring/parts/boardUi";
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
  board = false,
}: {
  stationId: string;
  version: number;
  initial: string;
  onSaved: (version: StationVersion) => void;
  /** The institution board's rail card. */
  board?: boolean;
}) {
  const scope = useAuthoringScope();
  const [brief, setBrief] = useState(initial);
  const [saved, setSaved] = useState(false);
  const action = useAction();

  if (board) {
    return (
      <div className={boardPad}>
        <h2 className="m-0 text-assess-desc font-semibold text-ink">Reading brief</h2>
        <p className={`m-0 ${boardMeta}`}>
          What the candidate reads before the station starts. Saving this does not cut a new version.
        </p>
        <Textarea
          aria-label="Reading brief"
          value={brief}
          rows={8}
          className={`${boardInput} py-2.5`}
          onChange={(e) => {
            setBrief(e.target.value);
            setSaved(false);
          }}
        />
        {action.error ? <Alert tone="danger">{action.error}</Alert> : null}
        <button
          type="button"
          className={`${boardBtn("default", true)} self-start`}
          disabled={action.busy !== null || brief === initial}
          onClick={() =>
            action.run("brief", async () => {
              onSaved(await editStationBrief(scope, stationId, version, brief));
              setSaved(true);
            })
          }
        >
          {action.busy === "brief" ? "Saving…" : "Save brief"}
        </button>
        {saved ? <span className={`${boardMeta} text-osce-success-text`}>Saved.</span> : null}
      </div>
    );
  }
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
