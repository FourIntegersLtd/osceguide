"use client";

import { useState } from "react";
import { cn } from "@/foundation/ui";
import { Note } from "@/domains/assess/ui";
import { SettingsCard } from "@/domains/assess/settings/SettingsCard";
import { errorMessage } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { setNonverbalFeedback, type Organization } from "@/domains/assess/api";
import { useAssessWords } from "@/capabilities/assess-words";
import { boardBtn } from "@/foundation/ui/boardKit";

/**
 * Whether trainees may turn on camera-based non-verbal feedback in self-practice.
 *
 * Off until an administrator allows it. The feedback is the trainee's alone and never part of a
 * mark or result. Not shown to employers: the feature is for self-practice, which hire does not have.
 */
export function NonverbalCard({ org, onSaved }: { org: Organization; onSaved: () => void }) {
  const w = useAssessWords();
  const { session } = useSession();
  const [enabled, setEnabled] = useState(org.nonverbal_feedback_enabled);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const changed = enabled !== org.nonverbal_feedback_enabled;

  // The server lets only an institution administrator change this; everyone else would meet a refusal on save.
  const mayChange = can(session, "sign_off_results");

  async function save() {
    setBusy(true);
    setFailure(null);
    setSaved(false);
    try {
      await setNonverbalFeedback(org.slug, enabled);
      setSaved(true);
      onSaved();
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  if (w.hiring || !mayChange) return null;

  return (
    <SettingsCard
      title="Non-verbal feedback in self-practice"
      lead={`Lets a ${w.trainee} turn on camera-based feedback on eye line, nodding and expression while they practise. The video stays on their device. Only they see the feedback; it is never part of a mark or a result.`}
    >
      {failure ? <Note tone="bad" role="alert">{failure}</Note> : null}
      {saved ? <Note tone="ok" role="status">Saved.</Note> : null}
      <label className="m-0 flex min-h-8 cursor-pointer items-start gap-2.5 text-assess-label font-normal">
        <input type="checkbox" checked={enabled} disabled={busy} onChange={(event) => setEnabled(event.target.checked)} className="mt-0.5 h-4 w-4" />
        Allow non-verbal feedback in self-practice
      </label>
      <button type="button" className={cn(boardBtn("primary"), "self-start")} onClick={() => void save()} disabled={!changed || busy}>
        {busy ? "Saving…" : "Save"}
      </button>
    </SettingsCard>
  );
}
