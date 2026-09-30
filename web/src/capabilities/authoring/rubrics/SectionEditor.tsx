"use client";

import { Badge, cn } from "@/foundation/ui";
import { useRubricBuilder } from "@/capabilities/authoring/rubrics/builderContext";
import { CompetencyList } from "@/capabilities/authoring/rubrics/CompetencyEditor";
import { FieldCard, FieldList } from "@/capabilities/authoring/rubrics/FieldEditor";
import { AddButton, ItemControls, ProblemNote, TextAtPath, ToggleAtPath } from "@/capabilities/authoring/rubrics/formParts";
import { getAt, isJsonObject, listAt, pathText, type JsonPath } from "@/capabilities/authoring/rubrics/jsonPath";
import { problemsAt, problemsWithin } from "@/capabilities/authoring/rubrics/problems";
import { appendAt, newSection } from "@/capabilities/authoring/rubrics/rubricEdits";
import { labelFor, SECTION_KINDS, type SectionKind } from "@/capabilities/authoring/rubrics/rubricVocabulary";

/**
 * The rubric's parts, top to bottom, as the feedback page will show them.
 *
 * Three kinds: a rated domain (competencies, each answered in the same
 * competency fields), a written section (fields answered once), and a single
 * field on its own. The cards follow the structure's own order, and moving a
 * card moves the part on the candidate's page.
 */
export function SectionList() {
  const { structure, edit, problems } = useRubricBuilder();
  const sections = listAt(structure, ["sections"]);
  return (
    <div className="space-y-4" data-path="sections">
      <ProblemNote messages={problemsAt(problems, ["sections"])} />
      {sections.length === 0 ? (
        <p className="rounded-osce-md border border-dashed border-osce-border p-6 text-center text-osce-meta text-ink-subtle">
          No parts yet. Add a rated domain to start.
        </p>
      ) : null}
      {sections.map((_section, index) => (
        <SectionCard key={index} index={index} count={sections.length} />
      ))}
      <div className="flex flex-wrap gap-2">
        {SECTION_KINDS.map((kind) => (
          <AddButton
            key={kind.value}
            label={kind.label}
            onClick={() => edit((current) => appendAt(current, ["sections"], newSection(current, kind.value)))}
          />
        ))}
      </div>
    </div>
  );
}

function SectionCard({ index, count }: { index: number; count: number }) {
  const { structure, problems } = useRubricBuilder();
  const path: JsonPath = ["sections", index];
  const section = getAt(structure, path);
  if (!isJsonObject(section)) return null;
  const kind = section.kind as SectionKind;
  const inside = problemsWithin(problems, path);
  return (
    <section
      data-path={pathText(path)}
      className={cn(
        "space-y-4 rounded-osce-lg border bg-osce-surface p-4 shadow-sm",
        inside > 0 ? "border-osce-danger/40" : "border-osce-border",
      )}
    >
      <header className="flex items-start gap-3">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={kind === "domain" ? "accent" : kind === "section" ? "info" : "neutral"} size="sm">
              {labelFor(SECTION_KINDS, kind)}
            </Badge>
            {inside > 0 ? (
              <Badge tone="danger" size="sm">
                {inside} {inside === 1 ? "problem" : "problems"}
              </Badge>
            ) : null}
          </div>
          <ProblemNote messages={problemsAt(problems, [...path, "kind"])} />
        </div>
        <ItemControls listPath={["sections"]} index={index} count={count} noun="part" />
      </header>

      {kind === "field" ? (
        <div className="space-y-3">
          <TextAtPath path={[...path, "title"]} label="Heading" />
          <FieldCard path={[...path, "field"]} />
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-[2fr_1fr]">
            <TextAtPath path={[...path, "title"]} label={kind === "domain" ? "Domain" : "Section"} placeholder="e.g. Data gathering" />
            <TextAtPath path={[...path, "id"]} label="Id" mono hint="Lower case and underscores; results are stored under it." />
          </div>
          <TextAtPath path={[...path, "instructions"]} label="Instructions to the marker" rows={2} />
          {kind === "domain" ? <DomainBody path={path} /> : <FieldList listPath={[...path, "fields"]} heading="Fields" />}
        </div>
      )}
    </section>
  );
}

/** A domain's switches, its competencies, what each competency answers and what the domain answers once. */
function DomainBody({ path }: { path: JsonPath }) {
  const { structure } = useRubricBuilder();
  const nullable = getAt(structure, [...path, "nullable"]) === true;
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <ToggleAtPath path={[...path, "live"]} label="Judged live" hint="Can be judged while the consultation is still running." />
        <ToggleAtPath path={[...path, "nullable"]} label="May be left out" hint="One of several alternatives; a result may leave it empty." />
      </div>
      {nullable ? <TextAtPath path={[...path, "description"]} label="What this alternative is" placeholder="e.g. Clinical station feedback (Station 2)" /> : null}
      <CompetencyList domainPath={path} />
      <FieldList listPath={[...path, "competencyFields"]} heading="Each competency answers" allowRating />
      {listAt(structure, [...path, "fields"]).length > 0 ? (
        <FieldList listPath={[...path, "fields"]} heading="Answered once for the domain" />
      ) : null}
    </div>
  );
}
