"use client";

import { useEffect, useMemo, useState } from "react";
import {
  HiOutlineArchiveBox,
  HiOutlineArrowLeft,
  HiOutlineArrowUpTray,
  HiOutlineDocumentDuplicate,
  HiOutlineTrash,
} from "react-icons/hi2";
import { Alert, Button } from "@/foundation/ui";
import { StationInstanceContentPanel } from "@/capabilities/authoring/sections/StationInstanceContentPanel";
import { validateStationContentScoped } from "@/capabilities/authoring/lib/b2cStationContentScope";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { AuthoringCard } from "@/capabilities/authoring/parts/AuthoringCard";
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
  supportsBrief,
  supportsVersionDelete,
  type Station,
  type StationTemplate,
  type StationVersion,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
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
  const action = useAction();

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
  }, [station.id, version]);

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
        className="inline-flex items-center gap-1.5 text-osce-body font-medium text-b2b-accent hover:underline"
      >
        <HiOutlineArrowLeft className="h-4 w-4 shrink-0" aria-hidden />
        Stations
      </button>

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <AuthoringCard padding="md">
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
                onClick={() =>
                  void action.run("archive", async () =>
                    setWorking(await archiveStationVersion(scope, station.id, version)),
                  )
                }
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
                onClick={() =>
                  void action.run("delete", async () => {
                    await deleteStationVersion(scope, station.id, version);
                    onBack();
                  })
                }
              >
                <HiOutlineTrash className="h-4 w-4" aria-hidden />
              </AuthoringIconAction>
            ) : null}
          </AuthoringRowActions>
        </div>

        {!structure && templateVersionId ? (
          <p className="mt-3 text-osce-caption text-b2b-mid">
            Template structure is not available in the catalogue — reload templates or edit from the
            template list.
          </p>
        ) : null}
        {!structure && !templateVersionId ? (
          <p className="mt-3 text-osce-caption text-b2b-mid">
            No layout is defined for exam {station.exam_code}. Import uses the B2C library shapes
            for sca, plab, casc and ortho only.
          </p>
        ) : null}

        <p className="mt-3 text-osce-caption text-b2b-mid">
          A published version is what an attempt was assessed against, so it is archived rather
          than deleted.
        </p>
      </AuthoringCard>

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
        <AuthoringCard padding="md">
          <p className="mb-4 text-osce-caption text-b2b-mid">
            Version {version}.
            {isDraft
              ? " Edit sections below, then save or publish."
              : " Published — same sections as B2C admin (read only). Create a new draft version to edit."}
          </p>
          <LegacyStationMeta content={editContent} stationTitle={station.title} />
          <StationInstanceContentPanel
            structure={structure}
            content={editContent}
            onChange={setEditContent}
            readOnly={!isDraft}
          />
          {isDraft ? (
            <div className="mt-6 flex justify-end border-t border-b2b-border pt-4">
              <Button
                type="button"
                variant="commit"
                disabled={!canSaveContent || action.busy !== null}
                onClick={() =>
                  void action.run("content", async () => {
                    if (structure) {
                      const v = validateStationContentScoped(structure, editContent);
                      if (!v.ok) {
                        throw new Error(v.errors[0] ?? "Please fill all required fields.");
                      }
                    }
                    setWorking(await editStationVersion(scope, station.id, version, editContent));
                  })
                }
              >
                {action.busy === "content" ? "Saving…" : "Save content"}
              </Button>
            </div>
          ) : null}
        </AuthoringCard>
      ) : null}
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
    <div className="mb-6 grid gap-4 rounded-lg border border-b2b-border bg-b2b-cream/40 p-4 md:grid-cols-2">
      {legacyId ? (
        <div>
          <p className="text-osce-caption font-medium text-b2b-mid">Station ID</p>
          <p className="mt-1 font-mono text-osce-body text-b2b-headline">{legacyId}</p>
        </div>
      ) : null}
      <div>
        <p className="text-osce-caption font-medium text-b2b-mid">Station name</p>
        <p className="mt-1 text-osce-body text-b2b-headline">{name}</p>
      </div>
    </div>
  );
}
