"use client";

import { useEffect, useId, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, AsyncBoundary, Badge, cn, getInputClassName, SectionSearchField } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { copyRubric, listRubricStartingPoints, type RubricStartingPoint } from "@/capabilities/authoring/api";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { labelFor, RATING_KINDS } from "@/capabilities/authoring/rubrics/rubricVocabulary";
import { PlatformTemplateWizardPageLayout } from "@/capabilities/authoring/templates/PlatformTemplateWizardPageLayout";
import { rubricEditPath, rubricsListPath } from "@/capabilities/authoring/templates/paths";

const KIND_WORDS: Record<RubricStartingPoint["kind"], string> = {
  blank: "Blank",
  platform: "OSCE Guide",
  own: "Yours",
};

/**
 * Where a new rubric starts: blank, a copy of one of the platform's published
 * rubrics, or (inside an organisation) a copy of one of its own.
 *
 * The backend lists the choices and does the copying; this screen names the
 * new rubric and picks one. The search runs on the server.
 */
export function RubricStartScreen() {
  const scope = useAuthoringScope();
  const { hrefFor } = useSurface();
  const router = useRouter();
  const action = useAction();
  const titleId = useId();
  const [title, setTitle] = useState("");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [chosen, setChosen] = useState<string>("blank");

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const points = useAsync((signal) => listRubricStartingPoints(scope, query, signal), [scope.base, query]);
  const keyOf = (point: RubricStartingPoint) => (point.kind === "blank" ? "blank" : `${point.rubric_id}:${point.version}`);
  const picked = (points.data?.items ?? []).find((point) => keyOf(point) === chosen) ?? null;

  const create = () =>
    void action.run("create", async () => {
      const rubric = await copyRubric(scope, {
        title: title.trim() || null,
        source_rubric_id: picked && picked.kind !== "blank" ? picked.rubric_id : null,
        source_version: picked && picked.kind !== "blank" ? picked.version : null,
      });
      const first = (rubric.versions ?? [])[0];
      router.push(rubricEditPath(hrefFor, rubric.id, first?.version ?? 1));
    });

  return (
    <PlatformTemplateWizardPageLayout
      eyebrow="Rubric"
      title="New rubric"
      subtitle="Start blank or from a published rubric. You get a draft to edit; nothing is used until you publish it."
      backHref={rubricsListPath(hrefFor)}
      backLabel="Rubrics"
    >
      <div className="space-y-5">
        <div className="max-w-lg">
          <label htmlFor={titleId} className="block text-osce-meta font-medium text-osce-ink-500">
            Title
          </label>
          <input
            id={titleId}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder={picked && picked.kind !== "blank" ? `Copy of ${picked.title}` : "e.g. Consultation skills"}
            className={cn(getInputClassName(), "mt-1")}
          />
          <p className="mt-0.5 text-osce-caption text-osce-ink-400">Set here; a rubric keeps its title across versions.</p>
        </div>

        <div className="space-y-3">
          <SectionSearchField value={search} onChange={setSearch} placeholder="Search published rubrics…" ariaLabel="Search starting points" />
          <AsyncBoundary state={points}>
            {(data) => (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" role="radiogroup" aria-label="Start from">
                {data.items.map((point) => (
                  <StartCard key={keyOf(point)} point={point} selected={keyOf(point) === chosen} onSelect={() => setChosen(keyOf(point))} />
                ))}
              </div>
            )}
          </AsyncBoundary>
        </div>

        {action.error ? <Alert tone="danger">{action.error}</Alert> : null}
        <div className="flex justify-end">
          <AuthoringButton variant="commit" isLoading={action.busy === "create"} disabled={action.busy !== null || !picked} onClick={create}>
            {picked?.kind === "blank" ? "Start blank" : "Copy and edit"}
          </AuthoringButton>
        </div>
      </div>
    </PlatformTemplateWizardPageLayout>
  );
}

function StartCard({ point, selected, onSelect }: { point: RubricStartingPoint; selected: boolean; onSelect: () => void }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={onSelect}
      className={cn(
        "flex h-full flex-col gap-2 rounded-osce-lg border p-4 text-left transition-colors",
        selected ? "border-osce-accent bg-osce-accent-subtle ring-2 ring-osce-accent-subtle" : "border-osce-border bg-osce-surface hover:border-osce-accent",
      )}
    >
      <div className="flex items-center gap-2">
        <Badge tone={point.kind === "blank" ? "neutral" : point.kind === "platform" ? "accent" : "info"} size="sm">
          {KIND_WORDS[point.kind]}
        </Badge>
        {point.kind !== "blank" ? <span className="text-osce-caption text-osce-ink-400">v{point.version}</span> : null}
      </div>
      <span className="text-osce-body font-semibold text-osce-ink-900">{point.title}</span>
      <span className="text-osce-caption text-osce-ink-500">
        {labelFor(RATING_KINDS, point.rating_kind)}
        {point.competency_count > 0 ? ` · ${point.competency_count} competencies` : ""}
      </span>
      {point.domains && point.domains.length > 0 ? (
        <span className="line-clamp-2 text-osce-caption text-osce-ink-400">{point.domains.join(" · ")}</span>
      ) : null}
    </button>
  );
}
