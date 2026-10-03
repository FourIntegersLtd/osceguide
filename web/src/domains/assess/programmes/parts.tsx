import type { ReactNode } from "react";
import { Alert, cn } from "@/foundation/ui";
import type { ProgrammeStage, ProgrammeStation } from "@/domains/assess/programmes/preview";

/**
 * Shown on every screen that has no API behind it yet.
 *
 * `needs` names the missing route in plain words, so the notice doubles as the
 * to-do list a reviewer reads off the screen.
 */
export function PreviewNotice({ needs }: { needs: string }) {
  return (
    <Alert tone="warning" title="Sample data">
      This screen is not connected yet, so the people and numbers on it are examples. {needs}
    </Alert>
  );
}

/** A titled card: the unit every programme screen is built from. */
export function Panel({
  title,
  action,
  children,
  className,
}: {
  title: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-panel border border-b2b-border bg-b2b-surface p-5", className)}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-osce-title font-semibold text-b2b-headline">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

/** The three stages a purpose moves people through, with where the cohort is. */
export function StageStrip({
  titles,
  stages,
}: {
  titles: readonly [string, string, string];
  stages: readonly [ProgrammeStage, ProgrammeStage, ProgrammeStage];
}) {
  return (
    <ol className="grid gap-3 md:grid-cols-3">
      {stages.map((stage, index) => (
        <li key={titles[index]} className="rounded-panel border border-b2b-border bg-b2b-surface p-5">
          <p className="text-osce-caption font-medium text-b2b-mid">
            {index + 1} · {titles[index]}
          </p>
          <p className="mt-2 text-osce-title font-semibold tabular-nums text-b2b-headline">{stage.figure}</p>
          <p className="mt-1 text-osce-meta text-b2b-mid">{stage.detail}</p>
        </li>
      ))}
    </ol>
  );
}

/** A share of a cohort, as a bar with its figure. */
export function Completion({ value }: { value: number }) {
  return (
    <span className="flex w-36 shrink-0 items-center gap-2">
      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-canvas" aria-hidden>
        <span className="block h-full rounded-full bg-accent" style={{ width: `${value}%` }} />
      </span>
      <span className="w-10 text-right text-osce-meta tabular-nums text-b2b-mid">{value}%</span>
    </span>
  );
}

export interface Column<Row> {
  header: string;
  cell: (row: Row) => ReactNode;
}

/** A plain table for a handful of rows; it scrolls in its own box on a phone. */
export function SimpleTable<Row>({
  columns,
  rows,
  rowKey,
}: {
  columns: Column<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-left text-osce-body text-b2b-headline">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.header} scope="col" className="pb-2 pr-4 text-osce-caption font-medium text-b2b-mid">
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-t border-b2b-border">
              {columns.map((column) => (
                <td key={column.header} className="py-3 pr-4 align-top">
                  {column.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A name with a quieter second line, as the first cell of a people table. */
export function Person({ name, detail }: { name: string; detail: string }) {
  return (
    <span className="block">
      <span className="block font-medium">{name}</span>
      <span className="block text-osce-meta text-b2b-mid">{detail}</span>
    </span>
  );
}

/** A wide column with a narrow one beside it; one column on a phone. */
export function Columns({ main, side }: { main: ReactNode; side: ReactNode }) {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <div className="flex min-w-0 flex-col gap-5">{main}</div>
      <div className="flex min-w-0 flex-col gap-5">{side}</div>
    </div>
  );
}

export function StationList({ stations }: { stations: ProgrammeStation[] }) {
  return (
    <ul className="flex flex-col divide-y divide-b2b-border">
      {stations.map((station) => (
        <li key={station.title} className="py-2.5 first:pt-0 last:pb-0">
          <p className="text-osce-body font-medium text-b2b-headline">{station.title}</p>
          <p className="text-osce-meta text-b2b-mid">{station.meta}</p>
        </li>
      ))}
    </ul>
  );
}
