"use client";

import { Checkbox, Select, cn } from "@/foundation/ui";
import { ChipRadioGroup } from "@/capabilities/authoring/rubrics/ChipRadioGroup";
import { inputClass as baseInput } from "@/capabilities/authoring/rubrics/inputClass";
import {
  SCORE_WORDS,
  isNumberScale,
  levelWord,
  problemsWithin,
  ruleSentence,
  scaleOf,
  updatePass,
  type PassPart,
  type Problem,
  type Rule,
  type Scale,
  type ScoreKind,
  type Scheme,
} from "@/capabilities/authoring/rubrics/schemeModel";

type RuleKind = "none" | "score" | "labels";
const inputClass = cn(baseInput, "w-20");

function bestValue(scale: Scale | undefined): string | boolean | number {
  return scale && !isNumberScale(scale) ? (scale.levels[1]?.value ?? scale.levels[0]?.value ?? "") : (scale?.to ?? 0);
}

/** One line of the pass rule: how to count, which rule, and the sentence the marker will apply. */
function RuleRow({
  which,
  title,
  part,
  scale,
  readOnly,
  onPart,
  extra,
  domainHasRule = true,
  problemPaths,
  problems,
}: {
  which: "domain" | "overall";
  title: string;
  part: PassPart | undefined;
  scale: Scale | undefined;
  readOnly: boolean;
  onPart: (part: PassPart | undefined) => void;
  extra?: React.ReactNode;
  /** The station sentence only mentions "every domain" while the domains have a pass line. */
  domainHasRule?: boolean;
  problemPaths: string;
  problems: readonly Problem[];
}) {
  const rule = part?.rule;
  const kind: RuleKind = rule ? rule.type : "none";
  const setKind = (next: RuleKind) => {
    if (next === kind) return;
    if (next === "none") {
      const { rule: _rule, ...rest } = part ?? {};
      return onPart(Object.keys(rest).length > 0 ? rest : undefined);
    }
    if (next === "score") return onPart({ ...part, score: part?.score && part.score !== "labels" ? part.score : "sum", rule: { type: "score", atLeast: 1 } });
    onPart({ ...part, score: "labels", rule: { type: "labels", atLeast: 1, of: "count", value: bestValue(scale) } });
  };
  const patchRule = (patch: Partial<Rule>) => onPart({ ...part, rule: { ...rule, ...patch } as Rule });
  const inner = problems.filter((p) => p.path === problemPaths || p.path.startsWith(`${problemPaths}.`));
  return (
    <div className="space-y-3 rounded-osce-md border border-osce-border p-4" data-path={problemPaths}>
      <h3 className="text-osce-body font-semibold text-ink">{title}</h3>
      <ChipRadioGroup
        label={`${title} pass line`}
        options={[{ id: "none", label: "No pass line" }, { id: "score", label: "A score of at least" }, { id: "labels", label: "Competencies rated at least" }] as const}
        value={kind}
        disabled={readOnly}
        onChange={setKind}
      />
      {rule?.type === "score" ? (
        <div className="flex flex-wrap items-center gap-2 text-osce-body text-ink">
          <label className="flex items-center gap-2">
            Count by
            <Select
              selectSize="sm"
              className="w-48"
              disabled={readOnly}
              data-path={`pass.${which}.score`}
              value={part?.score ?? "sum"}
              onChange={(event) => onPart({ ...part, score: event.target.value as ScoreKind })}
            >
              {(Object.keys(SCORE_WORDS) as ScoreKind[]).filter((k) => k !== "labels").map((k) => (
                <option key={k} value={k}>{SCORE_WORDS[k]}</option>
              ))}
            </Select>
          </label>
          <label className="flex items-center gap-2">
            at least
            <input type="number" data-path={`pass.${which}.rule.atLeast`} className={inputClass} readOnly={readOnly} value={rule.atLeast} onChange={(event) => patchRule({ atLeast: Number(event.target.value) })} />
          </label>
        </div>
      ) : null}
      {rule?.type === "labels" ? (
        <div className="flex flex-wrap items-center gap-2 text-osce-body text-ink">
          at least
          <input aria-label="At least" type="number" min={0} data-path={`pass.${which}.rule.atLeast`} className={inputClass} readOnly={readOnly} value={rule.atLeast} onChange={(event) => patchRule({ atLeast: Number(event.target.value) })} />
          <Select selectSize="sm" className="w-56" aria-label="Count as" disabled={readOnly} value={rule.of} onChange={(event) => patchRule({ of: event.target.value as "count" | "percent" })}>
            <option value="count">of the competencies</option>
            <option value="percent">percent of the competencies</option>
          </Select>
          rated
          {scale && !isNumberScale(scale) ? (
            <>
              <Select selectSize="sm" className="w-40" aria-label="Rated at least" data-path={`pass.${which}.rule.value`} disabled={readOnly} value={String(rule.value ?? "")} onChange={(event) => patchRule({ value: scale.levels.find((l) => String(l.value) === event.target.value)?.value ?? event.target.value })}>
                {rule.value === undefined ? <option value="">Pick a level</option> : null}
                {scale.levels.map((level) => (
                  <option key={String(level.value)} value={String(level.value)}>{levelWord(level)}</option>
                ))}
              </Select>
              or better
            </>
          ) : (
            <>
              <input aria-label="Rated at least" type="number" data-path={`pass.${which}.rule.value`} className={inputClass} readOnly={readOnly} value={Number(rule.value ?? 0)} onChange={(event) => patchRule({ value: Number(event.target.value) })} />
              or more
            </>
          )}
        </div>
      ) : null}
      {extra}
      <p className="rounded-osce-md bg-osce-canvas px-3 py-2 text-osce-meta text-ink-muted">{ruleSentence(which, part, scale, domainHasRule)}</p>
      {inner.map((p) => (
        <p key={`${p.path}-${p.message}`} className="text-osce-caption text-osce-danger-text">{p.message}</p>
      ))}
    </div>
  );
}

/** The pass rule for a domain and for the station, each read back as a sentence. */
export function PassRuleBlock({ scheme, onScheme, readOnly, problems }: { scheme: Scheme; onScheme: (s: Scheme) => void; readOnly: boolean; problems: readonly Problem[] }) {
  const scale = scaleOf(scheme);
  const domain = scheme.pass?.domain;
  const overall = scheme.pass?.overall;
  const outOf = scheme.advanced?.outOf;
  const domainRule = domain?.rule !== undefined;
  return (
    <div className="space-y-4" data-path="pass">
      <div>
        <h2 className="text-osce-body font-semibold text-ink">Pass rule</h2>
        <p className="text-osce-caption text-ink-muted">Read the sentence: it is exactly what the marker applies.</p>
      </div>
      <RuleRow which="domain" title="Domains" part={domain} scale={scale} readOnly={readOnly} problems={problems} problemPaths="pass.domain" onPart={(part) => onScheme(updatePass(scheme, "domain", part))} />
      <RuleRow
        which="overall"
        title="Station"
        part={overall}
        scale={scale}
        readOnly={readOnly}
        problems={problems}
        problemPaths="pass.overall"
        domainHasRule={domainRule}
        onPart={(part) => onScheme(updatePass(scheme, "overall", part))}
        extra={
          <div>
            <Checkbox
              label="Every domain must pass too"
              disabled={readOnly || !domainRule}
              checked={overall?.everyDomainPasses === true}
              onChange={(event) => onScheme(updatePass(scheme, "overall", { ...overall, everyDomainPasses: event.target.checked }))}
            />
            {!domainRule ? <p className="ml-7 text-osce-caption text-ink-subtle">Set a domain pass line first.</p> : null}
          </div>
        }
      />
      <label className="block max-w-60 text-osce-caption font-medium text-ink-muted">
        Total out of
        <input
          type="number"
          min={0}
          data-path="advanced.outOf"
          className={cn(baseInput, "mt-1")}
          readOnly={readOnly}
          placeholder="Worked out"
          value={typeof outOf === "number" ? outOf : ""}
          onChange={(event) => {
            const { outOf: _drop, ...rest } = scheme.advanced ?? {};
            onScheme({ ...scheme, advanced: event.target.value === "" ? rest : { ...rest, outOf: Number(event.target.value) } });
          }}
        />
        <span className="mt-1 block font-normal text-ink-subtle">Blank means worked out from the scale.</span>
      </label>
      <p className="text-osce-caption text-ink-muted">Bands such as Clear pass and Borderline cannot be set with these controls. They can only be set by editing the scheme text on the Advanced tab.</p>
      {problemsWithin(problems, ["pass"]) > 0 && !problems.some((p) => p.path.startsWith("pass.")) ? (
        <p className="text-osce-caption text-osce-danger-text">{problems.find((p) => p.path === "pass")?.message}</p>
      ) : null}
    </div>
  );
}
