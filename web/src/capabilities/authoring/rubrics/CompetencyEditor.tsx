"use client";

import { cn } from "@/foundation/ui";
import { useRubricBuilder } from "@/capabilities/authoring/rubrics/builderContext";
import { AddButton, GroupHeading, ItemControls, ProblemNote, TextAtPath } from "@/capabilities/authoring/rubrics/formParts";
import { listAt, pathText, setAt, type JsonPath } from "@/capabilities/authoring/rubrics/jsonPath";
import { problemsAt, problemsWithin } from "@/capabilities/authoring/rubrics/problems";
import { appendAt, newCompetency, readRating, textAt } from "@/capabilities/authoring/rubrics/rubricEdits";

/**
 * A domain's competencies: the skills a candidate is rated on, one grade each.
 *
 * On a graded rating (R/A/G or a named scale) each competency may also say
 * what earns each grade; those are its descriptors, keyed by the grade. A
 * number range or met / not met has no grades to describe, so they are not
 * offered there.
 */
export function CompetencyList({ domainPath }: { domainPath: JsonPath }) {
  const { structure, edit, problems } = useRubricBuilder();
  const listPath = [...domainPath, "competencies"];
  const competencies = listAt(structure, listPath);
  const rating = readRating(structure);
  const grades = rating.kind === "rag" || rating.kind === "scale" ? rating.scale : [];
  return (
    <div className="space-y-2" data-path={pathText(listPath)}>
      <GroupHeading count={competencies.length}>Competencies</GroupHeading>
      <ProblemNote messages={problemsAt(problems, listPath)} />
      {competencies.map((_competency, index) => {
        const path = [...listPath, index];
        return (
          <div
            key={index}
            data-path={pathText(path)}
            className={cn(
              "space-y-3 rounded-osce-md border bg-osce-surface p-3",
              problemsWithin(problems, path) > 0 ? "border-osce-danger/40" : "border-osce-border",
            )}
          >
            <div className="flex items-start gap-2">
              <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-[3fr_2fr]">
                <TextAtPath path={[...path, "label"]} label="Competency" placeholder="e.g. Explores the patient's concerns" />
                <TextAtPath path={[...path, "id"]} label="Id" mono />
              </div>
              <ItemControls listPath={listPath} index={index} count={competencies.length} noun="competency" />
            </div>
            <TextAtPath path={[...path, "instructions"]} label="What the marker looks for" rows={2} />
            {grades.length > 0 ? <Descriptors path={[...path, "descriptors"]} grades={grades} /> : null}
          </div>
        );
      })}
      <AddButton
        label="Add competency"
        onClick={() => edit((current) => appendAt(current, listPath, newCompetency(listAt(current, listPath))))}
      />
    </div>
  );
}

/** What earns each grade. An empty box removes that grade's descriptor. */
function Descriptors({ path, grades }: { path: JsonPath; grades: readonly string[] }) {
  const { structure, edit, problems, readOnly } = useRubricBuilder();
  return (
    <div className="space-y-1.5">
      <p className="text-osce-meta font-medium text-osce-ink-500">What earns each grade (optional)</p>
      <ProblemNote messages={problemsAt(problems, path)} />
      {grades.map((grade) => {
        const gradePath = [...path, grade];
        const messages = problemsAt(problems, gradePath);
        return (
          <div key={grade} className="flex items-start gap-2">
            <span className="mt-1.5 w-20 shrink-0 truncate text-osce-caption font-semibold text-osce-ink-500" title={grade}>
              {grade}
            </span>
            <div className="min-w-0 flex-1">
              <input
                type="text"
                aria-label={`Descriptor for ${grade}`}
                data-path={pathText(gradePath)}
                readOnly={readOnly}
                value={textAt(structure, gradePath)}
                onChange={(event) => {
                  const text = event.target.value;
                  edit((current) => setAt(current, gradePath, text === "" ? undefined : text));
                }}
                className="w-full rounded-osce-sm border border-osce-border bg-osce-surface px-2 py-1 text-osce-meta text-osce-ink-900 placeholder:text-osce-ink-400 focus:border-osce-accent focus:outline-none"
                placeholder={`A ${grade} looks like…`}
              />
              <ProblemNote messages={messages} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
