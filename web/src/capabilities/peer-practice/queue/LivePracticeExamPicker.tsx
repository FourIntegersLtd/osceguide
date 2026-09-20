"use client";

import { useAsync } from "@/foundation/hooks";
import { AsyncBoundary } from "@/foundation/ui";
import { listExams } from "@/capabilities/stations/api";

export function LivePracticeExamPicker({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const exams = useAsync((signal) => listExams(signal), []);
  return <AsyncBoundary state={exams} isEmpty={(page) => page.items.length === 0}
    empty={{ title: "No exams available", description: "Please try again later." }}>
    {(page) => <label className="my-4 flex flex-col gap-2">
      <span>Choose your exam</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}
        className="rounded-lg border border-border bg-surface p-3 text-ink">
        <option value="">Select an exam</option>
        {page.items.map((exam) => <option key={exam.code} value={exam.code}>{exam.name}</option>)}
      </select>
    </label>}
  </AsyncBoundary>;
}
