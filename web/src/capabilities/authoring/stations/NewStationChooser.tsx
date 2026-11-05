"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Select, SelectableCard } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { ImportStationDialog } from "@/capabilities/authoring/imports/ImportStationDialog";
import { useAuthoringExamCatalog } from "@/capabilities/authoring/parts/useAuthoringExamCatalog";
import { LoadError } from "@/capabilities/authoring/parts/LoadError";
import { PlatformTemplateWizardPageLayout } from "@/capabilities/authoring/templates/PlatformTemplateWizardPageLayout";
import { platformTemplateWizardFooterClass } from "@/capabilities/authoring/templates/wizardFooter";
import { stationLibraryPath, stationNewPath, stationsListPath } from "@/capabilities/authoring/stations/paths";
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
    else if (way === "library") router.push(stationLibraryPath(hrefFor));
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
              <SelectableCard key={w.id} selected={w.id === way} onSelect={() => setWay(w.id)}>
                <span className="text-osce-body font-medium text-ink">{w.title}</span>
                <span className="text-osce-caption text-ink-muted">{w.body}</span>
              </SelectableCard>
            ))}
          </div>
        </div>

        <div className="rounded-osce-lg border border-osce-border bg-osce-surface p-4">
          <p className="text-osce-body font-medium text-ink">What happens next</p>
          <p className="mt-1 text-osce-caption text-ink-muted">{current.next}</p>
        </div>
      </div>

      <div className={platformTemplateWizardFooterClass}>
        <Button type="button" variant="secondary" onClick={() => router.push(listHref)}>
          Cancel
        </Button>
        {examCode === "" ? (
          <p className="mr-auto text-osce-caption text-ink-muted">Choose an exam to continue.</p>
        ) : null}
        <Button type="button" variant="commit" disabled={examCode === ""} onClick={go}>
          {current.cta}
        </Button>
      </div>

      <ImportStationDialog open={importing} onClose={() => setImporting(false)} initialExamCode={examCode} />
    </PlatformTemplateWizardPageLayout>
  );
}
