"use client";

import { useEffect, useMemo, useState } from "react";
import {
  HiOutlineArchiveBox,
  HiOutlineArrowLeft,
  HiOutlineArrowUpTray,
  HiOutlineDocumentDuplicate,
  HiOutlineTrash,
} from "react-icons/hi2";
import { Alert, Button, ConfirmModal, Panel } from "@/foundation/ui";
import { StationInstanceContentPanel } from "@/capabilities/authoring/sections/StationInstanceContentPanel";
import { validateStationContentScoped } from "@/capabilities/authoring/lib/b2cStationContentScope";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { StationVersionHistory } from "@/capabilities/authoring/sections/StationVersionHistory";
import { StationUsedBy } from "@/capabilities/authoring/sections/StationUsedBy";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import {
  addStationVersion,
  archiveStationVersion,
  deleteStationVersion,
  editStationVersion,
  publishStationVersion,
  removeStationPhoto,
  supportsBrief,
  supportsFactCheck,
  supportsVersionDelete,
  uploadStationPhotos,
  type Station,
  type StationTemplate,
  type StationVersion,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import { StationFactCheck } from "@/capabilities/authoring/sections/StationFactCheck";
import type { Facts } from "@/capabilities/fact-check";
import { BriefEditor } from "@/capabilities/authoring/sections/BriefEditor";
import { legacyB2cStationStructure } from "@/capabilities/authoring/lib/legacyB2cStationStructure";

function structureForTemplateVersion(
  templates: StationTemplate[],
  templateVersionId: string | null | undefined,
): StationStructure | null {
  if (!templateVersionId) return null;
  for (const template of templates) {
    const version = template.versions.find((v) => v.id === templateVersionId);
    if (version) {
      return version.structure as StationStructure;
    }
  }
  return null;
}

/**
 * One station's working version: cut a draft, edit it, publish or archive it.
 */
export function StationDetail({
  station,
  templates,
  onBack,
}: {
  station: Station;
  templates: StationTemplate[];
  onBack: () => void;
}) {
  const scope = useAuthoringScope();
  const [working, setWorking] = useState<StationVersion | null>(null);
  const [editContent, setEditContent] = useState<Record<string, unknown>>({});
  /** Fact-check rulings made since the last save; they are saved with the content. */
  const [ruledFacts, setRuledFacts] = useState<Facts | null>(null);
  const action = useAction();
  const [confirming, setConfirming] = useState<"archive" | "delete" | null>(null);

  const version = working?.version ?? station.version;
  const status = working?.status ?? station.status;
  const isDraft = status !== "published" && status !== "archived";
  const templateVersionId = station.template_version_id ?? null;

  const structure = useMemo(() => {
    const fromTemplate = structureForTemplateVersion(templates, templateVersionId);
    if (fromTemplate) return fromTemplate;
    const src = (working?.content ?? station.content ?? {}) as Record<string, unknown>;
    return legacyB2cStationStructure(station.exam_code, src);
  }, [templates, templateVersionId, station.exam_code, station.content, working?.content]);

  useEffect(() => {
    const src = (working?.content ?? station.content ?? {}) as Record<string, unknown>;
    setEditContent({ ...src });
    setRuledFacts(null);
  }, [station.id, version]);

  /*
    Media is editable on a published version for the same reason the reading
    brief is: it is what a candidate is shown rather than what they are marked
    against, and an attempt freezes its own copy of the scenario. An archived
    version still refuses. The server writes the block, so its content wins.
  */
  const media =
    status === "archived"
      ? undefined
      : {
          upload: async (blockId: string, files: File[]) => {
            const result = await uploadStationPhotos(scope, station.id, version, blockId, files);
            setEditContent((result.version.content ?? {}) as Record<string, unknown>);
            return { uploaded: result.uploaded, failed: result.failed };
          },
          remove: async (url: string) => {
            const updated = await removeStationPhoto(scope, station.id, version, url);
            setEditContent((updated.content ?? {}) as Record<string, unknown>);
          },
        };

  async function handlePublish() {
    void action.run("publish", async () => {
      if (structure) {
        const v = validateStationContentScoped(structure, editContent);
        if (!v.ok) {
          throw new Error(v.errors[0] ?? "Please fill all required fields.");
        }
      }
      setWorking(await publishStationVersion(scope, station.id, version));
    });
  }

  const canSaveContent =
    structure !== null
      ? validateStationContentScoped(structure, editContent).ok
      : Object.keys(editContent).length > 0;

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-osce-body font-medium text-accent hover:underline"
      >
        <HiOutlineArrowLeft className="h-4 w-4 shrink-0" aria-hidden />
        Stations
      </button>

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <Panel padding="md">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-osce-body font-semibold text-ink">{station.title}</h2>
            <p className="mt-0.5 text-osce-caption text-ink-muted">
              {station.exam_code} · working on v{version}
            </p>
          </div>
          <StatusBadge status={status} />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <AuthoringRowActions>
            <AuthoringIconAction
              label="New draft version"
              busy={action.busy === "add"}
              busyLabel="Creating…"
              disabled={action.busy !== null}
              onClick={() =>
                void action.run("add", async () =>
                  setWorking(await addStationVersion(scope, station.id)),
                )
              }
            >
              <HiOutlineDocumentDuplicate className="h-4 w-4" aria-hidden />
            </AuthoringIconAction>
            {isDraft ? (
              <AuthoringIconAction
                variant="primary"
                label="Publish"
                busy={action.busy === "publish"}
                busyLabel="Publishing…"
                disabled={action.busy !== null}
                onClick={() => void handlePublish()}
              >
                <HiOutlineArrowUpTray className="h-4 w-4" aria-hidden />
              </AuthoringIconAction>
            ) : null}
            {status !== "archived" ? (
              <AuthoringIconAction
                variant="warning"
                label="Archive"
                busy={action.busy === "archive"}
                busyLabel="Archiving…"
                disabled={action.busy !== null}
                onClick={() => setConfirming("archive")}
              >
                <HiOutlineArchiveBox className="h-4 w-4" aria-hidden />
              </AuthoringIconAction>
            ) : null}
            {supportsVersionDelete(scope) && isDraft ? (
              <AuthoringIconAction
                variant="danger"
                label="Delete draft"
                busy={action.busy === "delete"}
                busyLabel="Deleting…"
                disabled={action.busy !== null}
                onClick={() => setConfirming("delete")}
              >
                <HiOutlineTrash className="h-4 w-4" aria-hidden />
              </AuthoringIconAction>
            ) : null}
          </AuthoringRowActions>
        </div>

        {!structure && templateVersionId ? (
          <p className="mt-3 text-osce-caption text-ink-muted">
            Template structure is not available in the catalogue. Reload templates or edit from the template list.
          </p>
        ) : null}
        {!structure && !templateVersionId ? (
          <p className="mt-3 text-osce-caption text-ink-muted">
            No layout is defined for exam {station.exam_code}. Import uses the B2C library shapes
            for sca, plab, casc and ortho only.
          </p>
        ) : null}

        <p className="mt-3 text-osce-caption text-ink-muted">
          A published version is what an attempt was assessed against, so it is archived rather
          than deleted.
        </p>
      </Panel>

      <ConfirmModal
        isOpen={confirming !== null}
        onCancel={() => {
          if (!action.busy) setConfirming(null);
        }}
        onConfirm={() => {
          const which = confirming;
          void action
            .run(which ?? "archive", async () => {
              if (which === "delete") {
                await deleteStationVersion(scope, station.id, version);
                onBack();
              } else {
                setWorking(await archiveStationVersion(scope, station.id, version));
              }
            })
            .then((ok) => {
              if (ok) setConfirming(null);
            });
        }}
        isLoading={confirming !== null && action.busy === confirming}
        title={
          confirming === "delete"
            ? `Delete draft v${version} of "${station.title}"?`
            : `Archive v${version} of "${station.title}"?`
        }
        confirmText={confirming === "delete" ? "Delete" : "Archive"}
        message={
          <>
            {confirming !== null ? <StationUsedBy stationId={station.id} version={version} /> : null}
            <span className="mt-1 block">
              {confirming === "delete"
                ? "The draft is removed. Published versions are untouched."
                : "Past attempts stay intact. The station is removed from the live library."}
            </span>
          </>
        }
      />

      {supportsBrief(scope) ? (
        <BriefEditor
          key={`${station.id}:${version}`}
          stationId={station.id}
          version={version}
          initial={readBrief(working?.content ?? station.content)}
          onSaved={setWorking}
        />
      ) : null}

      {structure ? (
        <Panel title="Station content">
          <p className="mb-4 text-osce-caption text-ink-muted">
            Version {version}.
            {isDraft
              ? " Edit sections below, then save or publish."
              : " Published, so it is read only. Create a new draft version to edit."}
          </p>
          <LegacyStationMeta content={editContent} stationTitle={station.title} />
          <StationInstanceContentPanel
            structure={structure}
            content={editContent}
            onChange={setEditContent}
            readOnly={!isDraft}
            media={media}
          />
          {isDraft ? (
            <div className="mt-6 flex justify-end border-t border-border pt-4">
              <Button
                type="button"
                variant="commit"
                disabled={!canSaveContent || action.busy !== null}
                onClick={() =>
                  action.run("content", async () => {
                    if (structure) {
                      const v = validateStationContentScoped(structure, editContent);
                      if (!v.ok) {
                        throw new Error(v.errors[0] ?? "Please fill all required fields.");
                      }
                    }
                    setWorking(
                      await editStationVersion(
                        scope,
                        station.id,
                        version,
                        editContent,
                        ruledFacts ?? undefined,
                      ),
                    );
                    setRuledFacts(null);
                  })
                }
              >
                {action.busy === "content" ? "Saving…" : "Save content"}
              </Button>
            </div>
          ) : null}
        </Panel>
      ) : null}

      {supportsFactCheck(scope) && status !== "archived" ? (
        <StationFactCheck
          scope={scope}
          stationId={station.id}
          version={version}
          content={editContent}
          onContentChange={setEditContent}
          onRuled={setRuledFacts}
          editable={isDraft}
          unsaved={
            ruledFacts !== null ||
            JSON.stringify(editContent) !==
              JSON.stringify(working?.content ?? station.content ?? {})
          }
        />
      ) : null}

      <StationVersionHistory stationId={station.id} />
    </div>
  );
}

function readBrief(content: unknown): string {
  if (!content || typeof content !== "object") return "";
  const brief = (content as { reading_brief?: unknown }).reading_brief;
  return typeof brief === "string" ? brief : "";
}

function LegacyStationMeta({
  content,
  stationTitle,
}: {
  content: Record<string, unknown>;
  stationTitle: string;
}) {
  const legacyId = typeof content.station_id === "string" ? content.station_id : "";
  const name =
    typeof content.station_name === "string" && content.station_name.trim()
      ? content.station_name
      : stationTitle;
  if (!legacyId && !name) return null;
  return (
    <div className="mb-6 grid grid-cols-1 gap-4 rounded-osce-lg border border-border bg-surface-raised/40 p-4 md:grid-cols-2">
      {legacyId ? (
        <div>
          <p className="text-osce-caption font-medium text-ink-muted">Station ID</p>
          <p className="mt-1 font-mono text-osce-body text-ink">{legacyId}</p>
        </div>
      ) : null}
      <div>
        <p className="text-osce-caption font-medium text-ink-muted">Station name</p>
        <p className="mt-1 text-osce-body text-ink">{name}</p>
      </div>
    </div>
  );
}
