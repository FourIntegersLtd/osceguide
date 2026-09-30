"use client";

import { useState } from "react";
import { B2CSegmentedTabs } from "@/foundation/ui";
import { RubricFeedback } from "@/capabilities/feedback";
import type { RubricDashboardPreview } from "@/capabilities/authoring/rubrics/dashboardSlot";
import type { FeedbackInputs } from "@/capabilities/authoring/rubrics/previewModel";

type PreviewView = "feedback" | "dashboard";

/**
 * What a candidate will see, drawn by the screens a candidate sees.
 *
 * The feedback tab is the real `RubricFeedback`; the dashboard tab is the
 * learner dashboard's own cards, passed in by the route because they live in
 * a domain. Both are fed the backend's sample result for the current draft,
 * so an author sees their rating, domains, pass lines and wording land.
 */
export function PreviewPane({
  inputs,
  dashboard: Dashboard,
  emptyMessage,
}: {
  inputs: FeedbackInputs | null;
  dashboard?: RubricDashboardPreview;
  emptyMessage: string;
}) {
  const [view, setView] = useState<PreviewView>("feedback");
  const items: { id: PreviewView; label: string }[] = [{ id: "feedback", label: "Feedback page" }];
  if (Dashboard) items.push({ id: "dashboard", label: "Dashboard" });
  const shown: PreviewView = Dashboard ? view : "feedback";
  return (
    <div className="space-y-3">
      {items.length > 1 ? <B2CSegmentedTabs items={items} value={shown} onChange={setView} compact aria-label="Preview" /> : null}
      {!inputs ? (
        <p className="rounded-osce-md border border-dashed border-osce-border p-6 text-center text-osce-meta text-ink-subtle">
          {emptyMessage}
        </p>
      ) : shown === "dashboard" && Dashboard ? (
        <div className="max-h-[70vh] overflow-y-auto">
          <Dashboard rating={inputs.rating} display={inputs.display} totals={inputs.totals} />
        </div>
      ) : (
        <div className="max-h-[70vh] overflow-y-auto rounded-osce-md border border-osce-border bg-osce-canvas p-3">
          <p className="mb-2 text-osce-caption text-ink-subtle">A made-up result, to show the layout.</p>
          <RubricFeedback rubric={inputs.rubric} result={inputs.result} narrow />
        </div>
      )}
    </div>
  );
}
