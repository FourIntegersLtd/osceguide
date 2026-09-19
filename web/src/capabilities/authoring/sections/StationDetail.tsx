"use client";

import { useState } from "react";
import { HiOutlineArrowLeft } from "react-icons/hi2";
import { Alert, Button, Card } from "@/foundation/ui";
import {
  addStationVersion,
  archiveStationVersion,
  deleteStationVersion,
  editStationVersion,
  publishStationVersion,
  supportsBrief,
  supportsVersionDelete,
  type Station,
  type StationVersion,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import { AuthoringDialog } from "@/capabilities/authoring/parts/AuthoringDialog";
import {
  JsonField,
  formatJson,
  jsonProblem,
  parseJson,
} from "@/capabilities/authoring/parts/JsonField";
import { BriefEditor } from "@/capabilities/authoring/sections/BriefEditor";

/**
 * One station's working version: cut a draft, edit it, publish or archive it.
 *
 * The backend serves no listing of a station's versions — only the row's
 * current one and the writes against it — so this screen holds the version it
 * is working on rather than offering a history. `docs/port-gaps.md` records
 * the missing read.
 */
export function StationDetail({ station, onBack }: { station: Station; onBack: () => void }) {
  const scope = useAuthoringScope();
  const [working, setWorking] = useState<StationVersion | null>(null);
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState("{}");
  const action = useAction();

  const version = working?.version ?? station.version;
  const status = working?.status ?? station.status;
  const isDraft = status !== "published" && status !== "archived";

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-osce-body font-medium text-b2b-accent hover:underline"
      >
        <HiOutlineArrowLeft className="h-4 w-4 shrink-0" aria-hidden />
        Stations
      </button>

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <Card themeType="b2b" padding="md">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-osce-body font-semibold text-b2b-headline">{station.title}</h2>
            <p className="mt-0.5 text-osce-caption text-b2b-mid">
              {station.exam_code} · working on v{version}
            </p>
          </div>
          <StatusBadge status={status} />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button
            themeType="b2b"
            variant="secondary"
            size="xs"
            disabled={action.busy !== null}
            onClick={() =>
              void action.run("add", async () => setWorking(await addStationVersion(scope, station.id)))
            }
          >
            {action.busy === "add" ? "Creating…" : "New draft version"}
          </Button>
          <Button
            themeType="b2b"
            variant="secondary"
            size="xs"
            disabled={!isDraft || action.busy !== null}
            onClick={() => {
              setContent(formatJson(working?.content ?? station.content ?? {}));
              setEditing(true);
            }}
          >
            Edit content
          </Button>
          <Button
            themeType="b2b"
            variant="commit"
            size="xs"
            disabled={!isDraft || action.busy !== null}
            onClick={() =>
              void action.run("publish", async () =>
                setWorking(await publishStationVersion(scope, station.id, version)),
              )
            }
          >
            {action.busy === "publish" ? "Publishing…" : "Publish"}
          </Button>
          <Button
            themeType="b2b"
            variant="secondary"
            size="xs"
            disabled={action.busy !== null}
            onClick={() =>
              void action.run("archive", async () =>
                setWorking(await archiveStationVersion(scope, station.id, version)),
              )
            }
          >
            {action.busy === "archive" ? "Archiving…" : "Archive"}
          </Button>
          {supportsVersionDelete(scope) ? (
            <Button
              themeType="b2b"
              variant="danger"
              size="xs"
              disabled={!isDraft || action.busy !== null}
              onClick={() =>
                void action.run("delete", async () => {
                  await deleteStationVersion(scope, station.id, version);
                  onBack();
                })
              }
            >
              {action.busy === "delete" ? "Deleting…" : "Delete draft"}
            </Button>
          ) : null}
        </div>

        <p className="mt-3 text-osce-caption text-b2b-mid">
          A published version is what an attempt was assessed against, so it is archived rather
          than deleted.
        </p>
      </Card>

      {supportsBrief(scope) ? (
        <BriefEditor
          key={`${station.id}:${version}`}
          stationId={station.id}
          version={version}
          initial={readBrief(working?.content ?? station.content)}
          onSaved={setWorking}
        />
      ) : null}

      <AuthoringDialog
        open={editing}
        title="Edit station content"
        lead="The station's content is the exam's own shape — what the template asked for."
        busy={action.busy === "content"}
        busyLabel="Saving…"
        commitLabel="Save"
        commitDisabled={jsonProblem(content) !== null}
        onClose={() => setEditing(false)}
        onCommit={() =>
          void action.run("content", async () => {
            setWorking(await editStationVersion(scope, station.id, version, parseJson(content)));
            setEditing(false);
          })
        }
      >
        <JsonField
          label="Content"
          hint={`Version ${version}. Only a draft can be edited.`}
          value={content}
          rows={14}
          onChange={setContent}
        />
      </AuthoringDialog>
    </div>
  );
}

function readBrief(content: unknown): string {
  if (!content || typeof content !== "object") return "";
  const brief = (content as { reading_brief?: unknown }).reading_brief;
  return typeof brief === "string" ? brief : "";
}
