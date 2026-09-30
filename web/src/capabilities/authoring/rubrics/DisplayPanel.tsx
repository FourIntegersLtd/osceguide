"use client";

import type { ReactNode } from "react";
import { useRubricBuilder } from "@/capabilities/authoring/rubrics/builderContext";
import {
  AddButton,
  ItemControls,
  NumberAtPath,
  ProblemNote,
  SelectAtPath,
  TextAtPath,
  ToggleAtPath,
} from "@/capabilities/authoring/rubrics/formParts";
import { listAt, pathText } from "@/capabilities/authoring/rubrics/jsonPath";
import { problemsAt } from "@/capabilities/authoring/rubrics/problems";
import { appendAt, readRating } from "@/capabilities/authoring/rubrics/rubricEdits";
import {
  DISPLAY_LABELS,
  DOMAIN_AGGREGATES,
  TONES,
  TOTAL_AGGREGATES,
} from "@/capabilities/authoring/rubrics/rubricVocabulary";

/**
 * How a result is summed up on the feedback page and the learner dashboard:
 * the `display` block of the structure.
 *
 * Every setting is optional; the backend fills a sensible default for the
 * rating (a R/A/G rubric counts grades, a range sums), and the preview beside
 * this panel shows what the defaults came to. Tones colour a number or a
 * met / not met; a graded scale is coloured by position, so tones are not
 * offered there (the backend refuses them).
 */
export function DisplayPanel() {
  const { structure, problems } = useRubricBuilder();
  const rating = readRating(structure);
  const toned = rating.kind === "range" || rating.kind === "boolean";
  return (
    <div className="space-y-6">
      <ProblemNote messages={problemsAt(problems, ["display"])} />
      <Block title="Each domain" description="The figure each domain gets, and the line a domain must reach.">
        <div className="grid gap-3 sm:grid-cols-2">
          <SelectAtPath path={["display", "domain", "aggregate"]} label="Domain result" choices={DOMAIN_AGGREGATES} emptyLabel="Default" />
          <NumberAtPath path={["display", "domain", "passAtLeast"]} label="Domain pass line" hint="Leave empty for no domain pass line." />
        </div>
      </Block>

      <Block title="Station total" description="The one figure for the whole station, and what passes.">
        <div className="grid gap-3 sm:grid-cols-3">
          <SelectAtPath path={["display", "total", "aggregate"]} label="Total" choices={TOTAL_AGGREGATES} emptyLabel="Default" />
          <NumberAtPath path={["display", "total", "max"]} label="Out of" hint="Empty: worked out from the rubric." />
          <NumberAtPath path={["display", "total", "passAtLeast"]} label="Pass line" />
        </div>
        <ToggleAtPath
          path={["display", "total", "requireEveryDomain"]}
          label="Every domain must pass too"
          hint="A station passes only if each domain reaches its own pass line."
        />
      </Block>

      {toned ? (
        <Block title="Tones" description="Colour a rating by how far up the scale it sits: atLeast is a fraction from 0 to 1.">
          <ToneList />
        </Block>
      ) : null}

      <Block title="Bands" description="Name ranges of the total, e.g. 0–4 “Not yet”, 5–7 “Borderline”.">
        <BandList />
      </Block>

      <Block title="Wording" description="Replace the default headings on the feedback page and dashboard.">
        <div className="grid gap-3 sm:grid-cols-2" data-path="display.labels">
          {DISPLAY_LABELS.map((label) => (
            <TextAtPath key={label.value} path={["display", "labels", label.value]} label={label.label} hint={label.hint} />
          ))}
        </div>
      </Block>
    </div>
  );
}

function Block({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <section className="space-y-3 rounded-osce-lg border border-osce-border bg-osce-surface p-4">
      <div>
        <h3 className="text-osce-body font-semibold text-ink">{title}</h3>
        <p className="text-osce-caption text-ink-muted">{description}</p>
      </div>
      {children}
    </section>
  );
}

function ToneList() {
  const { structure, edit, problems } = useRubricBuilder();
  const listPath = ["display", "tones"];
  const tones = listAt(structure, listPath);
  return (
    <div className="space-y-2" data-path={pathText(listPath)}>
      <ProblemNote messages={problemsAt(problems, listPath)} />
      {tones.map((_tone, index) => (
        <div key={index} className="flex items-start gap-2" data-path={pathText([...listPath, index])}>
          <div className="grid flex-1 gap-3 sm:grid-cols-2">
            <NumberAtPath path={[...listPath, index, "atLeast"]} label="From (0–1)" step="0.05" />
            <SelectAtPath path={[...listPath, index, "tone"]} label="Tone" choices={TONES} />
            <ProblemNote messages={problemsAt(problems, [...listPath, index])} />
          </div>
          <ItemControls listPath={listPath} index={index} count={tones.length} noun="tone" />
        </div>
      ))}
      {tones.length === 0 ? <p className="text-osce-caption text-ink-subtle">No tones: the default colours apply.</p> : null}
      <AddButton label="Add tone" onClick={() => edit((current) => appendAt(current, listPath, { atLeast: 0.5, tone: "good" }))} />
    </div>
  );
}

function BandList() {
  const { structure, edit, problems } = useRubricBuilder();
  const listPath = ["display", "bands"];
  const bands = listAt(structure, listPath);
  return (
    <div className="space-y-2" data-path={pathText(listPath)}>
      <ProblemNote messages={problemsAt(problems, listPath)} />
      {bands.map((_band, index) => (
        <div key={index} className="flex items-start gap-2" data-path={pathText([...listPath, index])}>
          <div className="grid flex-1 gap-3 sm:grid-cols-4">
            <NumberAtPath path={[...listPath, index, "from"]} label="From" />
            <NumberAtPath path={[...listPath, index, "to"]} label="To" />
            <TextAtPath path={[...listPath, index, "label"]} label="Name" />
            <SelectAtPath path={[...listPath, index, "tone"]} label="Tone" choices={TONES} emptyLabel="None" />
            <ProblemNote messages={problemsAt(problems, [...listPath, index])} />
          </div>
          <ItemControls listPath={listPath} index={index} count={bands.length} noun="band" />
        </div>
      ))}
      <AddButton label="Add band" onClick={() => edit((current) => appendAt(current, listPath, { from: 0, to: 1, label: "Band" }))} />
    </div>
  );
}
