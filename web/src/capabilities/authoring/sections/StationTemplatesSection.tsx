"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  HiOutlineArchiveBox,
  HiOutlineArrowUpTray,
  HiOutlineDocumentDuplicate,
  HiOutlinePencilSquare,
  HiOutlinePlusCircle,
  HiOutlineTrash,
} from "react-icons/hi2";
import { Alert, ConfirmModal } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import { AuthoringListRow } from "@/capabilities/authoring/parts/AuthoringListRow";
import { AuthoringCatalogFilterBar } from "@/capabilities/authoring/parts/AuthoringCatalogFilterBar";
import { AuthoringSectionLead } from "@/capabilities/authoring/parts/AuthoringSectionLead";
import { AUTHORING_ALL_EXAMS } from "@/capabilities/authoring/parts/examCatalogFilter";
import { useCursorPages } from "@/foundation/hooks";
import {
  addStationTemplateVersion,
  archiveStationTemplateVersion,
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
import { latestOf } from "@/capabilities/authoring/sections/versions";
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
  const { hrefFor } = useSurface();
  const router = useRouter();
  const [examFilter, setExamFilter] = useState(AUTHORING_ALL_EXAMS);
  const [search, setSearch] = useState("");
  // What the server is asked for: the box, once typing pauses.
  const [query, setQuery] = useState("");
  const [pendingConfirm, setPendingConfirm] = useState<TemplateRowConfirm | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

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

  const newHref =
    examFilter !== AUTHORING_ALL_EXAMS
      ? `${stationTemplateNewPath(hrefFor)}?exam=${encodeURIComponent(examFilter)}`
      : stationTemplateNewPath(hrefFor);

  return (
    <div className="space-y-4">
      <AuthoringSectionLead
        action={
          <AuthoringButton
            variant="commit"
            size="sm"
            className="gap-2"
            onClick={() => router.push(newHref)}
          >
            <HiOutlinePlusCircle className="h-4 w-4 shrink-0" aria-hidden />
            Create station template
          </AuthoringButton>
        }
      >
        Define layout and fields for clinical stations. Saved drafts and published
        versions appear below, but not the starting layouts on the new-template wizard.
      </AuthoringSectionLead>

      <AuthoringCatalogFilterBar
        examCode={examFilter}
        onExamCodeChange={setExamFilter}
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search templates…"
        searchAriaLabel="Search station templates"
      />

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <ListCard
        count={items.length}
        countLabel="Station templates"
        loading={templates.loading && !templates.data}
        error={templates.error ? templates.error.message : null}
        onDismissError={templates.reload}
        empty={{
          title: "No saved templates yet",
          description:
            "The layouts on New template are starting points only. They are not added here until you finish the wizard (Save draft), then Publish from this list.",
        }}
      >
        {items.map((template) => {
          const { published, draft } = latestOf(template.versions);
          const editHref =
            draft
              ? stationTemplateEditPath(hrefFor, template.id, draft.version)
              : null;
          return (
          <TemplateRow
            key={template.id}
            template={template}
            busy={action.busy}
            editHref={editHref}
            onAddVersion={() =>
              void action.run(`add:${template.id}`, () =>
                addStationTemplateVersion(scope, template.id),
              )
            }
            onPublish={() =>
              void action.run(`publish:${template.id}`, () =>
                publishStationTemplate(scope, template.id),
              )
            }
            onDeleteDraft={
              draft
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
              published
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

      <ConfirmModal
        isOpen={pendingConfirm !== null}
        onCancel={() => {
          if (!action.busy) setPendingConfirm(null);
        }}
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
            "Stations already built on it keep that shape; nothing new may bind to it."
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
  onAddVersion,
  onPublish,
  onDeleteDraft,
  onArchivePublished,
}: {
  template: StationTemplate;
  busy: string | null;
  editHref: string | null;
  onAddVersion: () => void;
  onPublish: () => void;
  onDeleteDraft?: () => void;
  onArchivePublished?: () => void;
}) {
  const { published, draft, archivedOnly } = latestOf(template.versions);
  const addBusy = busy === `add:${template.id}`;
  const publishBusy = busy === `publish:${template.id}`;
  const archiveBusy = busy === `archive:${template.id}`;
  const deleteBusy = busy === `delete:${template.id}`;

  return (
    <AuthoringListRow
      title={template.title}
      detail={
        <PublishStatusLine
          kindLabel={template.exam_code}
          published={published}
          draft={draft}
          archivedOnly={archivedOnly}
        />
      }
    >
      <AuthoringRowActions>
        <AuthoringIconAction
          label="New draft"
          busy={addBusy}
          busyLabel="Creating…"
          disabled={busy !== null}
          onClick={onAddVersion}
        >
          <HiOutlineDocumentDuplicate className="h-4 w-4" aria-hidden />
        </AuthoringIconAction>
        {editHref ? (
          <AuthoringIconAction label="Edit draft" href={editHref}>
            <HiOutlinePencilSquare className="h-4 w-4" aria-hidden />
          </AuthoringIconAction>
        ) : null}
        {draft ? (
          <AuthoringIconAction
            variant="primary"
            label="Publish draft"
            busy={publishBusy}
            busyLabel="Publishing…"
            disabled={busy !== null}
            onClick={onPublish}
          >
            <HiOutlineArrowUpTray className="h-4 w-4" aria-hidden />
          </AuthoringIconAction>
        ) : null}
        {onArchivePublished ? (
          <AuthoringIconAction
            variant="warning"
            label="Archive live"
            busy={archiveBusy}
            busyLabel="Archiving…"
            disabled={busy !== null}
            onClick={onArchivePublished}
          >
            <HiOutlineArchiveBox className="h-4 w-4" aria-hidden />
          </AuthoringIconAction>
        ) : null}
        {onDeleteDraft ? (
          <AuthoringIconAction
            variant="danger"
            label="Delete draft"
            busy={deleteBusy}
            busyLabel="Deleting…"
            disabled={busy !== null}
            onClick={onDeleteDraft}
          >
            <HiOutlineTrash className="h-4 w-4" aria-hidden />
          </AuthoringIconAction>
        ) : null}
      </AuthoringRowActions>
    </AuthoringListRow>
  );
}
