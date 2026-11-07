"use client";

import { useState } from "react";
import { cn } from "@/foundation/ui";
import { Note } from "@/domains/assess/ui";
import { SettingsCard } from "@/domains/assess/settings/SettingsCard";
import { errorMessage } from "@/foundation/hooks";
import { setRecordingRetention, type Organization } from "@/domains/assess/api";
import { RETENTION_CHOICES, retentionChoiceKey } from "@/domains/assess/results/appealsView";
import { useAssessWords } from "@/domains/assess/useAssessWords";
import { boardBtn, boardInput, boardLabel } from "@/foundation/ui/boardKit";

/**
 * How long a candidate's transcripts are kept once an attempt ends.
 *
 * Marks, decisions and the result ledger are never part of this: only what the candidate said.
 * The server's daily sweep applies the choice; a shorter period also reaches transcripts that are
 * already older than it, so the save is confirmed in words rather than silently.
 */
export function RetentionCard({ org, onSaved }: { org: Organization; onSaved: () => void }) {
  const w = useAssessWords();
  const [choice, setChoice] = useState(retentionChoiceKey(org.recording_retention_days));
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const changed = choice !== retentionChoiceKey(org.recording_retention_days) && choice !== "custom";

  async function save() {
    setBusy(true);
    setFailure(null);
    setSaved(false);
    try {
      await setRecordingRetention(org.slug, choice === "null" ? null : Number(choice));
      setSaved(true);
      onSaved();
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SettingsCard
      title="Keeping transcripts"
      lead={`How long what a ${w.trainee} said in a room is kept. Their marks and results are always kept.`}
    >
      {failure ? <Note tone="bad" role="alert">{failure}</Note> : null}
      {saved ? <Note tone="ok" role="status">Saved. Transcripts older than this are removed in the next daily clean-up.</Note> : null}
      <div>
        <label htmlFor="org-retention" className={boardLabel}>Keep transcripts for</label>
        <select id="org-retention" className={boardInput} value={choice} onChange={(event) => setChoice(event.target.value)}>
          {RETENTION_CHOICES.map((option) => (
            <option key={String(option.days)} value={String(option.days)}>{option.label}</option>
          ))}
          {choice === "custom" ? <option value="custom">{`${org.recording_retention_days} days (set by support)`}</option> : null}
        </select>
      </div>
      <button type="button" className={cn(boardBtn("primary"), "self-start")} onClick={() => void save()} disabled={!changed || busy}>
        {busy ? "Saving…" : "Save"}
      </button>
    </SettingsCard>
  );
}
