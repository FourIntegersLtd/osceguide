"use client";

import { useState } from "react";
import { HiOutlineChevronRight, HiOutlinePlusCircle } from "react-icons/hi2";
import { useRouter } from "next/navigation";
import { Alert } from "@/foundation/ui";
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
import { useCursorPages, useSearchQuery } from "@/foundation/hooks";
import { listRubrics, STATION_PAGE_LIMIT } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { ListCard } from "@/capabilities/authoring/parts/ListCard";
import { PublishStatusLine } from "@/capabilities/authoring/parts/StatusPills";
import { latestOf } from "@/capabilities/authoring/sections/versions";
import { RubricDetail } from "@/capabilities/authoring/sections/RubricDetail";
import { rubricNewPath } from "@/capabilities/authoring/templates/paths";

/**
 * Rubrics: what a station is marked against.
 *
 * The listing carries both the organisation's own marking schemes and the platform's,
 * because an institution may mark with either. Only its own can be edited, and
 * the backend says so rather than this screen guessing.
 */
export function RubricsSection() {
  const scope = useAuthoringScope();
  const { hrefFor } = useSurface();
  const router = useRouter();
  const [examFilter, setExamFilter] = useState(AUTHORING_ALL_EXAMS);
  const [search, setSearch] = useState("");
  // What the server is asked for: the box, once typing pauses.
  const query = useSearchQuery(search);

  // A page at a time, searched and exam-filtered in SQL — mirrors
  // StationsSection. Changing the exam filter or the search is in `deps`, so
  // either restarts paging from page one.
  const pages = useCursorPages(
    (cursor, signal) =>
      listRubrics(
        scope,
        {
          cursor,
          limit: STATION_PAGE_LIMIT,
          search: query,
          exam_code: examFilter || undefined,
        },
        signal,
      ),
    [scope.base, query, examFilter],
  );
  const rubrics = pages.state;
  const action = useAction(rubrics.reload);
  const items = rubrics.data ?? [];

  const [open, setOpen] = useState<string | null>(null);

  if (open) {
    return (
      <RubricDetail
        rubricId={open}
        onBack={() => {
          setOpen(null);
          rubrics.reload();
        }}
      />
    );
  }

  return (
    <div className="space-y-4">
      <AuthoringSectionLead
        action={
          <AuthoringButton
            variant="commit"
            size="sm"
            className="gap-2"
            onClick={() => router.push(rubricNewPath(hrefFor))}
          >
            <HiOutlinePlusCircle className="h-4 w-4 shrink-0" aria-hidden />
            Create marking scheme
          </AuthoringButton>
        }
      >
        The marking structure a station is assessed against.
      </AuthoringSectionLead>

      <AuthoringCatalogFilterBar
        examCode={examFilter}
        onExamCodeChange={setExamFilter}
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search marking schemes…"
        searchAriaLabel="Search marking schemes"
      />

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <ListCard
        count={items.length}
        countLabel="Marking schemes"
        loading={rubrics.loading && !rubrics.data}
        error={rubrics.error ? rubrics.error.message : null}
        onDismissError={rubrics.reload}
        empty={{
          title: "No marking schemes",
          description:
            "Create a marking scheme, publish a version, then build exams and templates on it.",
        }}
      >
        {items.map((rubric) => {
          const { published, draft, archivedOnly } = latestOf(
            rubric.versions ?? [],
          );
          return (
            <AuthoringListRow
              key={rubric.id}
              title={rubric.title}
              detail={
                <PublishStatusLine
                  kindLabel={
                    rubric.owner_kind === "platform" ? "OSCE Guide" : null
                  }
                  published={published}
                  draft={draft}
                  archivedOnly={archivedOnly}
                />
              }
              onOpen={() => setOpen(rubric.id)}
            >
              <AuthoringRowActions>
                <AuthoringIconAction
                  variant="ghost"
                  label="Open versions"
                  onClick={() => setOpen(rubric.id)}
                >
                  <HiOutlineChevronRight className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
              </AuthoringRowActions>
            </AuthoringListRow>
          );
        })}
      </ListCard>

      {pages.moreError ? (
        <Alert tone="danger">
          Could not load more rubrics: {pages.moreError.message}
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
            {pages.loadingMore ? "Loading…" : "Load more marking schemes"}
          </AuthoringButton>
        </div>
      ) : null}
    </div>
  );
}
