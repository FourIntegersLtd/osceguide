"use client";

import { useMemo, useState } from "react";
import { HiOutlineChevronRight, HiOutlinePlusCircle } from "react-icons/hi2";
import { Alert, getInputClassName } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import { AuthoringListRow } from "@/capabilities/authoring/parts/AuthoringListRow";
import { AuthoringCatalogFilterBar } from "@/capabilities/authoring/parts/AuthoringCatalogFilterBar";
import { AuthoringSectionLead } from "@/capabilities/authoring/parts/AuthoringSectionLead";
import { AUTHORING_ALL_EXAMS } from "@/capabilities/authoring/parts/examCatalogFilter";
import { useAuthoringExamCatalog } from "@/capabilities/authoring/parts/useAuthoringExamCatalog";
import { useAsync } from "@/foundation/hooks";
import { createRubric, listRubrics } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { ListCard } from "@/capabilities/authoring/parts/ListCard";
import { PublishStatusLine } from "@/capabilities/authoring/parts/StatusPills";
import { AuthoringDialog } from "@/capabilities/authoring/parts/AuthoringDialog";
import { JsonField, jsonProblem, parseJson } from "@/capabilities/authoring/parts/JsonField";
import { latestOf } from "@/capabilities/authoring/sections/versions";
import { RubricDetail } from "@/capabilities/authoring/sections/RubricDetail";
import {
  emptyMarkingLayout,
  markingLayoutToJson,
} from "@/capabilities/authoring/templates/rubricMarkingLayout";

/**
 * Rubrics: what a station is marked against.
 *
 * The listing carries both the organisation's own rubrics and the platform's,
 * because an institution may mark with either. Only its own can be edited, and
 * the backend says so rather than this screen guessing.
 */
export function RubricsSection() {
  const scope = useAuthoringScope();
  const { rubricVersionIdForExam } = useAuthoringExamCatalog();
  const [examFilter, setExamFilter] = useState(AUTHORING_ALL_EXAMS);
  const [search, setSearch] = useState("");
  const rubrics = useAsync((signal) => listRubrics(scope, {}, signal), [scope.base]);
  const action = useAction(rubrics.reload);

  const [creating, setCreating] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [structure, setStructure] = useState("{}");
  const [pacing, setPacing] = useState("{}");

  const items = useMemo(() => {
    const rubricForExam = rubricVersionIdForExam(examFilter);
    const q = search.trim().toLowerCase();
    return (rubrics.data?.items ?? []).filter((rubric) => {
      if (examFilter) {
        if (!rubricForExam) return false;
        const versionIds = (rubric.versions ?? []).map((v) => v.id);
        if (!versionIds.includes(rubricForExam)) return false;
      }
      if (!q) return true;
      return rubric.title.toLowerCase().includes(q) || rubric.id.toLowerCase().includes(q);
    });
  }, [rubrics.data, examFilter, search, rubricVersionIdForExam]);

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
            onClick={() => setCreating(true)}
          >
            <HiOutlinePlusCircle className="h-4 w-4 shrink-0" aria-hidden />
            Create rubric
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
        searchPlaceholder="Search rubrics…"
        searchAriaLabel="Search rubrics"
      />

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <ListCard
        count={items.length}
        countLabel="Rubrics"
        loading={rubrics.loading && !rubrics.data}
        error={rubrics.error ? rubrics.error.message : null}
        onDismissError={rubrics.reload}
        empty={{
          title: "No rubrics",
          description: "Create a rubric, publish a version, then build exams and templates on it.",
        }}
      >
        {items.map((rubric) => {
          const { published, draft, archivedOnly } = latestOf(rubric.versions ?? []);
          return (
            <AuthoringListRow
              key={rubric.id}
              title={rubric.title}
              detail={
                <PublishStatusLine
                  kindLabel={rubric.owner_kind === "platform" ? "OSCE Guide" : null}
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

      <AuthoringDialog
        open={creating}
        title="Create rubric"
        lead="The first version is a draft. Publish it when the structure is settled."
        error={action.error}
        busy={action.busy === "create"}
        busyLabel="Creating…"
        commitLabel="Create rubric"
        commitDisabled={
          title.trim() === "" ||
          prompt.trim() === "" ||
          jsonProblem(structure) !== null ||
          jsonProblem(pacing) !== null
        }
        onClose={() => setCreating(false)}
        onCommit={() =>
          void action.run("create", async () => {
            await createRubric(scope, {
              title: title.trim(),
              system_prompt: prompt,
              structure: parseJson(structure),
              pacing: parseJson(pacing),
              ...(scope.kind === "platform"
                ? { marking_layout: markingLayoutToJson(emptyMarkingLayout()) }
                : {}),
            });
            setTitle("");
            setPrompt("");
            setStructure("{}");
            setPacing("{}");
            setCreating(false);
          })
        }
      >
        <div>
          <label htmlFor="rubrics-section-title" className="block text-osce-body font-semibold text-b2b-headline">Title</label>
          <input
            id="rubrics-section-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={`mt-1 ${getInputClassName()}`}
            placeholder="e.g. Consultation skills"
          />
        </div>
        <div>
          <label htmlFor="rubrics-section-system-prompt" className="block text-osce-body font-semibold text-b2b-headline">
            System prompt
          </label>
          <p className="mt-0.5 text-osce-caption text-b2b-mid">
            What the marking engine is told before it reads a transcript.
          </p>
          <textarea
            id="rubrics-section-system-prompt"
            value={prompt}
            rows={6}
            onChange={(e) => setPrompt(e.target.value)}
            className="mt-1 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline focus:border-osce-accent focus:outline-none focus:ring-2 focus:ring-osce-accent-subtle"
          />
        </div>
        <JsonField label="Structure" value={structure} onChange={setStructure} />
        <JsonField label="Pacing" rows={6} value={pacing} onChange={setPacing} />
      </AuthoringDialog>
    </div>
  );
}
