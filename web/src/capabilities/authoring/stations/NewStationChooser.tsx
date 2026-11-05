"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Select } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { ImportStationDialog } from "@/capabilities/authoring/imports/ImportStationDialog";
import { useAuthoringExamCatalog } from "@/capabilities/authoring/parts/useAuthoringExamCatalog";
import { LoadError } from "@/capabilities/authoring/parts/LoadError";
import { PlatformTemplateWizardPageLayout } from "@/capabilities/authoring/templates/PlatformTemplateWizardPageLayout";
import { platformTemplateWizardFooterClass } from "@/capabilities/authoring/templates/wizardFooter";
import { stationNewPath, stationsListPath } from "@/capabilities/authoring/stations/paths";
import {
  STATION_START_WAYS,
  stationStartHref,
  type StationStartWay,
} from "@/capabilities/authoring/stations/stationStart";

/** "New station": the exam it is for, then how to start. The form opens on that choice. */
export function NewStationChooser() {
  const router = useRouter();
  const { hrefFor } = useSurface();
  const listHref = stationsListPath(hrefFor);
  const catalog = useAuthoringExamCatalog();
  const [examCode, setExamCode] = useState("");
  const [way, setWay] = useState<StationStartWay>("layout");
  const [importing, setImporting] = useState(false);
  const current = STATION_START_WAYS.find((w) => w.id === way) ?? STATION_START_WAYS[0]!;

  function go() {
    if (way === "import") setImporting(true);
    else if (way === "library") router.push(hrefFor("/stations"));
    else router.push(stationStartHref(stationNewPath(hrefFor), way, examCode));
  }

  return (
    <PlatformTemplateWizardPageLayout
      title="New station"
      backHref={listHref}
      backLabel="Stations"
    >
      <div className="space-y-6 p-5 sm:p-6">
        <div>
          <label htmlFor="new-station-exam" className="block text-osce-body font-semibold text-ink">
            For exam
          </label>
          <Select
            id="new-station-exam"
            value={examCode}
            onChange={(e) => setExamCode(e.target.value)}
            className="mt-1"
          >
            <option value="">{catalog.loading ? "Loading exams…" : "Select an exam…"}</option>
            {catalog.exams.map((exam) => (
              <option key={exam.code} value={exam.code}>
                {exam.name}
              </option>
            ))}
          </Select>
          <p className="mt-1 text-osce-caption text-ink-muted">
            Only exams that are ready show here. A station can only go into sittings of its own exam.
          </p>
          {catalog.error ? <LoadError message={catalog.error} onRetry={catalog.reload} /> : null}
        </div>

        <div>
          <p className="text-osce-body font-semibold text-ink">How do you want to start?</p>
          <div role="radiogroup" aria-label="How do you want to start?" className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {STATION_START_WAYS.map((w) => (
              <button
                key={w.id}
                type="button"
                role="radio"
                aria-checked={w.id === way}
                onClick={() => setWay(w.id)}
                className={[
                  "flex min-h-[92px] flex-col gap-1 rounded-osce-lg border p-4 text-left",
                  w.id === way ? "border-osce-accent bg-osce-accent-subtle" : "border-border bg-white",
                ].join(" ")}
              >
                <span className="text-osce-body font-medium text-ink">{w.title}</span>
                <span className="text-osce-caption text-ink-muted">{w.body}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-osce-lg border border-border bg-surface-raised/40 p-4">
          <p className="text-osce-body font-medium text-ink">What happens next</p>
          <p className="mt-1 text-osce-caption text-ink-muted">{current.next}</p>
        </div>
      </div>

      <div className={platformTemplateWizardFooterClass}>
        <Button type="button" variant="secondary" onClick={() => router.push(listHref)}>
          Cancel
        </Button>
        <Button type="button" variant="commit" onClick={go}>
          {current.cta}
        </Button>
      </div>

      <ImportStationDialog open={importing} onClose={() => setImporting(false)} onChanged={() => undefined} />
    </PlatformTemplateWizardPageLayout>
  );
}
