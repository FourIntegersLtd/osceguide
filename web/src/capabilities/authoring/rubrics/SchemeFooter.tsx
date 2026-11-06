"use client";

import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import type { TabFooter } from "@/capabilities/authoring/rubrics/schemeTabs";

/** Back, where you are, and Next under the tab; on the last step Next is Publish and a `stuck` reason replaces the position. */
export function SchemeFooter({ footer, readOnly, stuck, onBack, onNext }: { footer: TabFooter; readOnly: boolean; stuck: string | null; onBack: () => void; onNext: () => void }) {
  return (
    <div className="flex items-center justify-between gap-2 border-t border-osce-border pt-3">
      <AuthoringButton variant="ghost" size="sm" disabled={!footer.back} onClick={onBack}>{footer.backLabel}</AuthoringButton>
      <span id="scheme-footer-where" className="text-center text-osce-caption text-ink-muted">{stuck ?? footer.where}</span>
      {footer.nextLabel ? (
        <AuthoringButton variant="secondary" size="sm" aria-describedby="scheme-footer-where" disabled={(footer.next === null && readOnly) || stuck !== null} onClick={onNext}>
          {footer.nextLabel}
        </AuthoringButton>
      ) : <span />}
    </div>
  );
}
