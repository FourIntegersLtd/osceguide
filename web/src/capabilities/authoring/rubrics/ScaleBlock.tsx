"use client";

import { useState } from "react";
import { ConfirmModal, Select, cn } from "@/foundation/ui";
import { ChipRadioGroup } from "@/capabilities/authoring/rubrics/ChipRadioGroup";
import { inputClass } from "@/capabilities/authoring/rubrics/inputClass";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import {
  SCALE_PRESETS,
  addLevel,
  applyPreset,
  presetClearsTones,
  presetMovesRules,
  removeLevel,
  isNumberScale,
  problemsAt,
  problemsWithin,
  updateScale,
  type Level,
  type Problem,
  type Scale,
  type Scheme,
} from "@/capabilities/authoring/rubrics/schemeModel";

const nowNameOf = (scale: Scale | undefined) => SCALE_PRESETS.find((p) => p.id === scale?.id)?.label ?? scale?.name ?? "this scale";
const sameScale = (a: Scale | undefined, b: Scale) => a !== undefined && JSON.stringify({ ...a, id: "" }) === JSON.stringify({ ...b, id: "" });

/** How each competency is rated: a preset to start from, then the levels and their points. */
export function ScaleBlock({ scheme, onScheme, readOnly, problems }: { scheme: Scheme; onScheme: (s: Scheme) => void; readOnly: boolean; problems: readonly Problem[] }) {
  const scale = scheme.scales?.[0];
  const [pending, setPending] = useState<string | null>(null);
  // Switching clears what earns each level and re-points the pass rules, so ask first when anything would change.
  const hasDescriptions = scheme.outline.some((b) => b.block === "domain" && b.competencies.some((c) => Object.keys(c.descriptors ?? {}).length > 0));
  const choose = (id: string) => (hasDescriptions || presetClearsTones(scheme) || presetMovesRules(scheme, id) ? setPending(id) : onScheme(applyPreset(scheme, id)));
  const patchLevels = (change: (levels: Level[]) => Level[]) => {
    if (scale && !isNumberScale(scale)) onScheme(updateScale(scheme, { ...scale, levels: change(scale.levels) }));
  };
  const rising = scale && !isNumberScale(scale) && scale.levels.some((l, i) => i > 0 && l.points > (scale.levels[i - 1] as Level).points);
  const own = [...problemsAt(problems, ["scales"]), ...problemsAt(problems, ["scales", 0])];
  const presetName = SCALE_PRESETS.find((p) => p.id === pending)?.label ?? "";
  const pendingNumber = pending !== null && isNumberScale(SCALE_PRESETS.find((p) => p.id === pending)?.scale);
  const clears = hasDescriptions ? [pendingNumber ? "Your descriptions of each level will be deleted, because number ratings have no named levels." : `The level descriptions you wrote for ${nowNameOf(scale)} will be deleted.`] : [];
  const moves = pending !== null && presetMovesRules(scheme, pending) ? ["Your pass rules will be moved onto the new rating scale. Check them on the Pass rule tab."] : [];
  const tones = presetClearsTones(scheme) ? ["The score colours you set under Advanced will be removed, because they only suit the old scale. You can set them again."] : [];
  const switchMessage = [...clears, ...moves, ...tones, "Instructions and competencies stay."].join(" ");

  return (
    <div className="space-y-4" data-path="scales">
      <div>
        <h2 className="text-osce-body font-semibold text-ink">Scale</h2>
        <p className="text-osce-caption text-ink-muted">How each competency is rated. Best first. One scale for every domain.</p>
      </div>
      {readOnly ? null : (
        <ChipRadioGroup
          label="Start from"
          leading={<span className="text-osce-caption text-ink-muted">Start from</span>}
          options={SCALE_PRESETS.map((p) => ({ id: p.id, label: p.label }))}
          value={SCALE_PRESETS.find((p) => sameScale(scale, p.scale))?.id ?? null}
          onChange={choose}
        />
      )}
      {scale && !isNumberScale(scale) ? (
        <div className="space-y-2">
          <div className="grid grid-cols-[minmax(0,1fr)_96px_80px] gap-2 text-osce-caption text-ink-subtle">
            <span>Level</span>
            <span>Points</span>
            <span />
          </div>
          {scale.levels.map((level, j) => (
            <div key={`${String(level.value)}-${j}`} className="grid grid-cols-[minmax(0,1fr)_96px_80px] items-center gap-2">
              <input
                aria-label="Level"
                data-path={`scales[0].levels[${j}].label`}
                className={inputClass}
                readOnly={readOnly}
                value={level.label ?? String(level.value)}
                onChange={(event) => patchLevels((levels) => levels.map((l, i) => (i === j ? { ...l, label: event.target.value } : l)))}
              />
              <input
                aria-label="Points"
                data-path={`scales[0].levels[${j}].points`}
                type="number"
                min={0}
                className={inputClass}
                readOnly={readOnly}
                value={level.points}
                onChange={(event) => patchLevels((levels) => levels.map((l, i) => (i === j ? { ...l, points: Number(event.target.value) } : l)))}
              />
              {readOnly || scale.levels.length <= 2 ? (
                <span />
              ) : (
                <AuthoringButton variant="ghost" size="sm" onClick={() => onScheme(removeLevel(scheme, j))}>
                  Remove
                </AuthoringButton>
              )}
            </div>
          ))}
          {rising ? <p className="text-osce-caption text-osce-danger-text">Points must go down as you go down the list. Put the best level at the top, or lower the points of the levels below it.</p> : null}
          {own.map((message) => (
            <p key={message} className="text-osce-caption text-osce-danger-text">{message}</p>
          ))}
          {problemsWithin(problems, ["scales"]) > own.length
            ? problems.filter((p) => p.path.startsWith("scales[0].levels")).map((p) => (
                <p key={`${p.path}-${p.message}`} className="text-osce-caption text-osce-danger-text">{p.message}</p>
              ))
            : null}
          {readOnly ? null : (
            <AuthoringButton
              variant="ghost"
              size="sm"
              onClick={() => onScheme(addLevel(scheme))}
            >
              Add level
            </AuthoringButton>
          )}
          <p className="text-osce-caption text-ink-muted">Each level is worth points. The total adds them up. Put the best level first.</p>
        </div>
      ) : null}
      {scale && isNumberScale(scale) ? (
        <div className="space-y-2">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <label className="block text-osce-caption font-medium text-ink-muted">
              From
              <input type="number" data-path="scales[0].from" className={cn(inputClass, "mt-1")} readOnly={readOnly} value={scale.from} onChange={(event) => onScheme(updateScale(scheme, { ...scale, from: Number(event.target.value) }))} />
            </label>
            <label className="block text-osce-caption font-medium text-ink-muted">
              To
              <input type="number" data-path="scales[0].to" className={cn(inputClass, "mt-1")} readOnly={readOnly} value={scale.to} onChange={(event) => onScheme(updateScale(scheme, { ...scale, to: Number(event.target.value) }))} />
            </label>
            <div className="text-osce-caption font-medium text-ink-muted">
              Steps
              <Select className="mt-1" selectSize="sm" disabled={readOnly} value={scale.step} onChange={(event) => onScheme(updateScale(scheme, { ...scale, step: event.target.value as "whole" | "any" }))}>
                <option value="whole">Whole numbers</option>
                <option value="any">Any number</option>
              </Select>
            </div>
          </div>
          {own.map((message) => (
            <p key={message} className="text-osce-caption text-osce-danger-text">{message}</p>
          ))}
          <p className="text-osce-caption text-ink-muted">The marker gives each competency a number in this range.</p>
        </div>
      ) : null}
      {!scale ? <p className="text-osce-caption text-osce-danger-text">Choose how competencies are rated, for example Good / Fair / Poor, to continue.</p> : null}
      <ConfirmModal
        isOpen={pending !== null}
        title={`Switch to ${presetName}?`}
        message={switchMessage}
        confirmText="Switch scale"
        onCancel={() => setPending(null)}
        onConfirm={() => {
          if (pending) onScheme(applyPreset(scheme, pending));
          setPending(null);
        }}
      />
    </div>
  );
}
