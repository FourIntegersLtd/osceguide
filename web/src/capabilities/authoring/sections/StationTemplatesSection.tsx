"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import { importLabel, layoutKindLabel, layoutsLead, newLayoutLabel } from "@/capabilities/authoring/lib/authoringCopy";
import { AuthoringConfirm } from "@/capabilities/authoring/parts/AuthoringConfirm";
import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  HiOutlineArchiveBox,
  HiOutlineArrowUpTray,
  HiOutlineCloudArrowUp,
  HiOutlineDocumentDuplicate,
  HiOutlineDocumentPlus,
  HiOutlinePencilSquare,
  HiOutlinePlusCircle,
  HiOutlineTrash,
} from "react-icons/hi2";
import { Alert } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { AuthoringLeadButton } from "@/capabilities/authoring/parts/AuthoringLeadButton";
import { boardStack } from "@/capabilities/authoring/parts/boardUi";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import { AuthoringActionMenu } from "@/capabilities/authoring/parts/AuthoringActionMenu";
import { AuthoringListRow } from "@/capabilities/authoring/parts/AuthoringListRow";
import { AuthoringCatalogFilterBar } from "@/capabilities/authoring/parts/AuthoringCatalogFilterBar";
import { AuthoringSectionLead } from "@/capabilities/authoring/parts/AuthoringSectionLead";
import { AUTHORING_ALL_EXAMS } from "@/capabilities/authoring/parts/examCatalogFilter";
import { useCursorPages, useSearchQuery } from "@/foundation/hooks";
import {
  addStationTemplateVersion,
  archiveStationTemplateVersion,
  copyStationTemplate,
  deleteStationTemplateVersion,
  listStationTemplatesPage,
  STATION_PAGE_LIMIT,
  publishStationTemplate,
  type StationTemplate,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { ListCard } from "@/capabilities/authoring/parts/ListCard";
import { PublishStatusLine } from "@/capabilities/authoring/parts/StatusPills";
import { ImportStationDialog } from "@/capabilities/authoring/imports/ImportStationDialog";
import { canManageTemplate, latestOf } from "@/capabilities/authoring/sections/versions";
import {
  stationTemplateEditPath,
  stationTemplateNewPath,
} from "@/capabilities/authoring/templates/paths";

type TemplateRowConfirm =
  | {
      kind: "delete-draft";
      templateId: string;
      title: string;
      draftVersion: number;
      liveVersion: number | null;
    }
  | {
      kind: "archive-live";
      templateId: string;
      liveVersion: number;
    };

function confirmActionKey(confirm: TemplateRowConfirm): string {
  return confirm.kind === "delete-draft"
    ? `delete:${confirm.templateId}`
    : `archive:${confirm.templateId}`;
}

/**
 * Station templates: the layout and fields a station is built on.
 */
export function StationTemplatesSection() {
  const scope = useAuthoringScope();
  const org = !useAuthoringChrome().b2c;
  const { hrefFor } = useSurface();
  const router = useRouter();
  const w = useAssessWords();
  const [examFilter, setExamFilter] = useState(AUTHORING_ALL_EXAMS);
  const [search, setSearch] = useState("");
  // What the server is asked for: the box, once typing pauses.
  const query = useSearchQuery(search);
  const [pendingConfirm, setPendingConfirm] = useState<TemplateRowConfirm | null>(null);
  const [importing, setImporting] = useState(false);

  // A page at a time, searched and exam-filtered in SQL — mirrors
  // StationsSection. Changing the exam filter or the search is in `deps`, so
  // either restarts paging from page one.
  const pages = useCursorPages(
    (cursor, signal) =>
      listStationTemplatesPage(
        scope,
        { cursor, limit: STATION_PAGE_LIMIT, search: query, exam_code: examFilter || undefined },
        signal,
      ),
    [scope.base, query, examFilter],
  );
  const templates = pages.state;
  const action = useAction(templates.reload);
  const items = templates.data ?? [];

  const newHref = stationTemplateNewPath(hrefFor, examFilter !== AUTHORING_ALL_EXAMS ? examFilter : null);

  return (
    <div className={org ? boardStack : "space-y-4"}>
      <AuthoringSectionLead
        action={
          <>
            <AuthoringLeadButton icon={HiOutlineCloudArrowUp} onClick={() => setImporting(true)}>
              {importLabel(w)}
            </AuthoringLeadButton>
            <AuthoringLeadButton primary icon={HiOutlinePlusCircle} onClick={() => router.push(newHref)}>
              {newLayoutLabel(w)}
            </AuthoringLeadButton>
          </>
        }
      >
        {layoutsLead(w)}
      </AuthoringSectionLead>

      <AuthoringCatalogFilterBar
        examCode={examFilter}
        onExamCodeChange={setExamFilter}
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search templates…"
        searchAriaLabel="Search station templates"
      />

      {action.error && pendingConfirm === null ? <Alert tone="danger">{action.error}</Alert> : null}

      <ListCard
        count={items.length}
        countLabel="Station templates"
        loading={templates.loading && !templates.data}
        error={templates.error ? templates.error.message : null}
        onDismissError={templates.reload}
        empty={{
          title: "No saved templates yet",
          description: w.hiring ? "Layouts are only starting points. A template shows here once you Save draft. Publish it from this list to use it for stations." : "The layouts on New template are starting points only. They are not added here until you finish the wizard (Save draft), then Publish from this list.",
        }}
      >
        {items.map((template) => {
          const { published, draft } = latestOf(template.versions);
          const manageable = canManageTemplate(scope.kind, template.owner_kind);
          const editHref =
            draft && manageable
              ? stationTemplateEditPath(hrefFor, template.id, draft.version)
              : null;
          return (
          <TemplateRow
            key={template.id}
            template={template}
            busy={action.busy}
            editHref={editHref}
            viewHref={published ? stationTemplateEditPath(hrefFor, template.id, published.version) : null}
            onCopy={
              scope.kind === "org" &&
              template.owner_kind === "platform" &&
              published &&
              // Copied already: copying again would only give back the same copy.
              !items.some((own) => own.copied_from_id === template.id)
                ? () =>
                    void action.run(`copy:${template.id}`, () =>
                      copyStationTemplate(scope, template.id),
                    )
                : undefined
            }
            onAddVersion={
              // An organisation copies a platform template; only the platform edits it.
              scope.kind === "org" && template.owner_kind === "platform"
                ? undefined
                : () =>
                    void action.run(`add:${template.id}`, () =>
                      addStationTemplateVersion(scope, template.id),
                    )
            }
            onPublish={
              manageable
                ? () =>
                    void action.run(`publish:${template.id}`, () =>
                      publishStationTemplate(scope, template.id),
                    )
                : undefined
            }
            onDeleteDraft={
              draft && manageable
                ? () =>
                    setPendingConfirm({
                      kind: "delete-draft",
                      templateId: template.id,
                      title: template.title,
                      draftVersion: draft.version,
                      liveVersion: published?.version ?? null,
                    })
                : undefined
            }
            onArchivePublished={
              published && manageable
                ? () =>
                    setPendingConfirm({
                      kind: "archive-live",
                      templateId: template.id,
                      liveVersion: published.version,
                    })
                : undefined
            }
          />
          );
        })}
      </ListCard>

      {pages.moreError ? (
        <Alert tone="danger">
          Could not load more templates: {pages.moreError.message}
        </Alert>
      ) : null}
      {pages.hasMore ? (
        <div className="flex justify-center">
          <AuthoringButton
            variant="secondary"
            size="sm"
            disabled={pages.loadingMore}
            onClick={pages.loadMore}
          >
            {pages.loadingMore ? "Loading…" : "Load more templates"}
          </AuthoringButton>
        </div>
      ) : null}

      <ImportStationDialog
        open={importing}
        onClose={() => setImporting(false)}
        onChanged={templates.reload}
      />

      <AuthoringConfirm
        isOpen={pendingConfirm !== null}
        onCancel={() => {
          if (action.busy) return;
          action.clearError();
          setPendingConfirm(null);
        }}
        error={action.error}
        onConfirm={() => {
          if (!pendingConfirm) return;
          const confirm = pendingConfirm;
          void action.run(confirmActionKey(confirm), async () => {
            if (confirm.kind === "delete-draft") {
              await deleteStationTemplateVersion(
                scope,
                confirm.templateId,
                confirm.draftVersion,
              );
            } else {
              await archiveStationTemplateVersion(
                scope,
                confirm.templateId,
                confirm.liveVersion,
              );
            }
          }).then((ok) => {
            if (ok) setPendingConfirm(null);
          });
        }}
        isLoading={
          pendingConfirm !== null && action.busy === confirmActionKey(pendingConfirm)
        }
        tone={pendingConfirm?.kind === "delete-draft" ? "danger" : "default"}
        title={
          pendingConfirm?.kind === "archive-live"
            ? `Archive live v${pendingConfirm.liveVersion}?`
            : pendingConfirm?.liveVersion != null
              ? "Delete draft?"
              : pendingConfirm
                ? `Delete "${pendingConfirm.title}"?`
                : "Confirm"
        }
        confirmText={
          pendingConfirm?.kind === "archive-live"
            ? "Archive live"
            : pendingConfirm?.kind === "delete-draft"
              ? "Delete draft"
              : "Confirm"
        }
        message={
          pendingConfirm?.kind === "archive-live" ? (
            w.hiring ? "Stations already made from it are not affected. New stations can no longer use it." : "Stations already built on it keep that shape; nothing new may bind to it."
          ) : pendingConfirm?.kind === "delete-draft" ? (
            pendingConfirm.liveVersion != null ? (
              <>
                Draft v{pendingConfirm.draftVersion} will be removed permanently. Live v
                {pendingConfirm.liveVersion} stays published.
              </>
            ) : (
              "This removes the template entirely."
            )
          ) : (
            ""
          )
        }
      />
    </div>
  );
}

function TemplateRow({
  template,
  busy,
  editHref,
  viewHref,
  onCopy,
  onAddVersion,
  onPublish,
  onDeleteDraft,
  onArchivePublished,
}: {
  template: StationTemplate;
  busy: string | null;
  editHref: string | null;
  /** The live version, opened read only from the title; null while nothing is published. */
  viewHref: string | null;
  /** Set on a platform template seen from an organisation, which copies it rather than edits it. */
  onCopy?: () => void;
  /** Absent on a platform template seen from an organisation. */
  onAddVersion?: () => void;
  /** Absent on a platform template seen from an organisation. */
  onPublish?: () => void;
  onDeleteDraft?: () => void;
  onArchivePublished?: () => void;
}) {
  const { published, draft, archivedOnly } = latestOf(template.versions);
  const copyBusy = busy === `copy:${template.id}`;
  const addBusy = busy === `add:${template.id}`;
  const publishBusy = busy === `publish:${template.id}`;
  const archiveBusy = busy === `archive:${template.id}`;
  const deleteBusy = busy === `delete:${template.id}`;
  const router = useRouter();
  const w = useAssessWords();

  return (
    <AuthoringListRow
      title={template.title}
      onOpen={viewHref ? () => router.push(viewHref) : undefined}
      linkTitle
      detail={
        <PublishStatusLine
          kindLabel={onCopy ? [template.exam_code, "Platform template"].filter(Boolean).join(" · ") : layoutKindLabel(template.exam_code, template.copied_from_id, w)}
          published={published}
          draft={draft}
          archivedOnly={archivedOnly}
        />
      }
    >
      <AuthoringRowActions write>
        {/* One inline primary by status; the rest live in the menu. */}
        {onCopy ? (
          <AuthoringIconAction
            text="Copy to my organisation"
            variant="primary"
            label="Copy to my organisation"
            busy={copyBusy}
            busyLabel="Copying…"
            disabled={busy !== null}
            onClick={onCopy}
          >
            <HiOutlineDocumentPlus className="h-4 w-4" aria-hidden />
          </AuthoringIconAction>
        ) : editHref ? (
          <AuthoringIconAction label="Edit draft" text="Edit draft" href={editHref}>
            <HiOutlinePencilSquare className="h-4 w-4" aria-hidden />
          </AuthoringIconAction>
        ) : onAddVersion ? (
          <AuthoringIconAction
            text="New draft"
            label="New draft"
            busy={addBusy}
            busyLabel="Creating…"
            disabled={busy !== null}
            onClick={onAddVersion}
          >
            <HiOutlineDocumentDuplicate className="h-4 w-4" aria-hidden />
          </AuthoringIconAction>
        ) : null}
        <AuthoringActionMenu
          label={`Actions for ${template.title}`}
          items={[
            !onCopy && !!editHref && onAddVersion && {
              label: addBusy ? "Creating…" : "New draft",
              icon: <HiOutlineDocumentDuplicate className="h-4 w-4" />,
              disabled: busy !== null,
              onSelect: onAddVersion,
            },
            draft && onPublish && {
              label: publishBusy ? "Publishing…" : "Publish draft",
              icon: <HiOutlineArrowUpTray className="h-4 w-4" />,
              disabled: busy !== null,
              onSelect: onPublish,
            },
            onArchivePublished && {
              label: archiveBusy ? "Archiving…" : "Archive live",
              icon: <HiOutlineArchiveBox className="h-4 w-4" />,
              disabled: busy !== null,
              onSelect: onArchivePublished,
            },
            onDeleteDraft && {
              label: deleteBusy ? "Deleting…" : "Delete draft",
              icon: <HiOutlineTrash className="h-4 w-4" />,
              tone: "danger" as const,
              disabled: busy !== null,
              onSelect: onDeleteDraft,
            },
          ]}
        />
      </AuthoringRowActions>
    </AuthoringListRow>
  );
}
