"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import { stationExamHint } from "@/capabilities/authoring/lib/authoringCopy";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { B2CPageHeader, Button, Select, SelectableCard, cn } from "@/foundation/ui";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";
import { useSurface } from "@/capabilities";
import { ImportStationDialog } from "@/capabilities/authoring/imports/ImportStationDialog";
import { useAuthoringExamCatalog } from "@/capabilities/authoring/parts/useAuthoringExamCatalog";
import { LoadError } from "@/capabilities/authoring/parts/LoadError";
import { PlatformTemplateWizardPageLayout } from "@/capabilities/authoring/templates/PlatformTemplateWizardPageLayout";
import { platformTemplateWizardFooterClass } from "@/capabilities/authoring/templates/wizardFooter";
import { stationLibraryPath, stationNewPath, stationsListPath } from "@/capabilities/authoring/stations/paths";
import {
  stationStartWays,
  stationStartHref,
  type StationStartWay,
} from "@/capabilities/authoring/stations/stationStart";
import { boardBtn } from "@/foundation/ui/boardKit";

/** "New station": the exam it is for, then how to start. The form opens on that choice. */
export function NewStationChooser() {
  const router = useRouter();
  const words = useAssessWords();
  const { hrefFor } = useSurface();
  const listHref = stationsListPath(hrefFor);
  const catalog = useAuthoringExamCatalog();
  // An exam page sends its own code, so the choice is already made.
  const [examCode, setExamCode] = useState(useSearchParams().get("exam") ?? "");
  const [way, setWay] = useState<StationStartWay>("layout");
  const [importing, setImporting] = useState(false);
  const ways = stationStartWays(words);
  const current = ways.find((w) => w.id === way) ?? ways[0]!;

  function go() {
    if (way === "import") setImporting(true);
    else if (way === "library") router.push(stationLibraryPath(hrefFor));
    else router.push(stationStartHref(stationNewPath(hrefFor), way, examCode));
  }

  const chrome = useAuthoringChrome();
  if (!chrome.b2c) {
    /* An ordinary page: the header, the fields on the page canvas, the actions underneath. */
    return (
      <div className="flex flex-col gap-6 pb-8" data-testid="new-station-sheet">
        <div className="flex flex-col gap-6">
          <B2CPageHeader
            board
            action={<span aria-hidden />}
            className="!mb-0 [&_h1]:-mt-1"
            wideSubtitle
            eyebrow="Exams › Stations"
            title="New station"
            back={{ href: listHref, label: "Stations" }}
          />
          <div className="flex flex-col gap-[18px]">
            <div className="max-w-xl">
              <label htmlFor="new-station-exam" className="mb-1.5 block text-assess-label font-medium text-ink">For exam</label>
              <Select
                id="new-station-exam"
                value={examCode}
                onChange={(e) => setExamCode(e.target.value)}
                className="[&>select]:min-h-11 [&>select]:text-assess-desc"
              >
                <option value="">{catalog.loading ? "Loading exams…" : "Select an exam…"}</option>
                {catalog.exams.map((exam) => (
                  <option key={exam.code} value={exam.code}>{exam.name}</option>
                ))}
              </Select>
              <div className="mt-1.5 text-assess-meta text-ink-subtle">
                {stationExamHint(words)}
              </div>
              {catalog.error ? <LoadError message={catalog.error} onRetry={catalog.reload} /> : null}
            </div>
            <div>
              <div className="mb-2 text-assess-label font-medium text-ink">How do you want to start?</div>
              <div role="radiogroup" aria-label="How do you want to start?" className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {ways.map((w) => (
                  <button
                    key={w.id}
                    type="button"
                    role="radio"
                    aria-checked={w.id === way}
                    onClick={() => setWay(w.id)}
                    className={cn(
                      "flex min-h-[92px] flex-col gap-1 rounded-board border p-4 text-left text-ink",
                      w.id === way ? "border-osce-accent bg-assess-selected-bg" : "border-osce-border bg-osce-surface",
                    )}
                  >
                    <span className="text-assess-desc font-medium !leading-[normal]">{w.title}</span>
                    <span className="text-assess-meta text-ink-subtle">{w.body}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="rounded-board border border-osce-border-light bg-osce-canvas px-4 py-3.5">
              <div className="mb-1 text-assess-label font-medium">What happens next</div>
              <div className="text-assess-meta text-ink-subtle">{current.next}</div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            <Link href={listHref} className={boardBtn()}>Cancel</Link>
            <button type="button" className={boardBtn("primary")} disabled={examCode === ""} onClick={go}>{current.cta}</button>
            {examCode === "" ? <p className="m-0 text-assess-meta text-ink-subtle">Choose an exam to continue.</p> : null}
          </div>
        </div>
        <ImportStationDialog open={importing} onClose={() => setImporting(false)} initialExamCode={examCode} />
      </div>
    );
  }

  return (
    <PlatformTemplateWizardPageLayout
      title="New station"
      backHref={listHref}
      backLabel="Stations"
    >
      <div className="space-y-8 p-6 sm:p-8">
        <div>
          <label htmlFor="new-station-exam" className="block text-osce-body font-semibold text-ink">
            For exam
          </label>
          <Select
            id="new-station-exam"
            value={examCode}
            onChange={(e) => setExamCode(e.target.value)}
            className="mt-2"
          >
            <option value="">{catalog.loading ? "Loading exams…" : "Select an exam…"}</option>
            {catalog.exams.map((exam) => (
              <option key={exam.code} value={exam.code}>
                {exam.name}
              </option>
            ))}
          </Select>
          <p className="mt-2 text-osce-caption text-ink-muted">
            {stationExamHint(words)}
          </p>
          {catalog.error ? <LoadError message={catalog.error} onRetry={catalog.reload} /> : null}
        </div>

        <div>
          <p className="text-osce-body font-semibold text-ink">How do you want to start?</p>
          <div role="radiogroup" aria-label="How do you want to start?" className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {ways.map((w) => (
              <SelectableCard key={w.id} selected={w.id === way} onSelect={() => setWay(w.id)}>
                <span className="text-osce-body font-medium text-ink">{w.title}</span>
                <span className="text-osce-caption text-ink-muted">{w.body}</span>
              </SelectableCard>
            ))}
          </div>
        </div>

        <div className="rounded-osce-lg border border-osce-border bg-osce-surface p-5">
          <p className="text-osce-body font-medium text-ink">What happens next</p>
          <p className="mt-2 text-osce-caption text-ink-muted">{current.next}</p>
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
