"use client";

import { useState } from "react";
import { Button, Modal, Textarea } from "@/foundation/ui";
import { parseHandClaims, type HandClaim } from "@/capabilities/staff-media/parts/handCheck";

/** Records a fact check a person did themselves, in place of the platform's check. */
export function HandCheckModal({
  open,
  busy,
  error,
  onClose,
  onSubmit,
}: {
  open: boolean;
  busy: boolean;
  /** A failure from the server, shown beside the form's own. */
  error: string | null;
  onClose: () => void;
  onSubmit: (claims: HandClaim[]) => void;
}) {
  const [text, setText] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  if (!open) return null;

  const submit = () => {
    const parsed = parseHandClaims(text);
    setProblem(parsed.error);
    if (parsed.claims) onSubmit(parsed.claims);
  };

  return (
    <Modal onClose={onClose} title="Record a check done by hand" width="min(42rem, 96vw)">
      <div className="flex flex-col gap-3 p-4">
        {problem || error ? (
          <p className="text-osce-meta text-osce-danger-text">{problem ?? error}</p>
        ) : null}
        <Textarea
          aria-label="Claims checked by hand"
          label="One claim per line, with the page it was checked against"
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={10}
          placeholder="ECG for exertional chest pain || NICE CG95"
        />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" isLoading={busy} onClick={submit}>
            Record check
          </Button>
        </div>
      </div>
    </Modal>
  );
}
