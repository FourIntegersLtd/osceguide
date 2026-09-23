"use client";

const GRADE_STYLES: Record<"R" | "A" | "G", string> = {
  R: "bg-osce-danger-bg text-osce-danger-text ring-osce-danger-icon",
  A: "bg-osce-warning-bg text-osce-warning-text ring-osce-warning-icon",
  G: "bg-osce-success-bg text-osce-success-text ring-osce-success-icon",
};

export function RagGradeToggle({
  grade,
  selected,
  disabled,
  onPick,
}: {
  grade: "R" | "A" | "G";
  selected: boolean;
  disabled: boolean;
  onPick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onPick}
      className={[
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-osce-body font-bold transition ring-2 ring-offset-0 ring-offset-white sm:h-10 sm:w-10 sm:text-osce-body",
        selected
          ? GRADE_STYLES[grade]
          : "bg-osce-canvas text-osce-ink-500 ring-transparent hover:bg-osce-border-light",
        disabled ? "cursor-default opacity-60" : "cursor-pointer",
      ].join(" ")}
      aria-pressed={selected}
      title={grade === "R" ? "Red" : grade === "A" ? "Amber" : "Green"}
    >
      {grade}
    </button>
  );
}

export function RagDomainTotals({
  counts,
}: {
  counts: { G: number; A: number; R: number; total: number };
}) {
  return (
    <div className="mt-2 rounded-lg border border-osce-border bg-osce-surface px-3 py-2 text-osce-body text-osce-ink-700">
      <p className="font-medium text-osce-ink-700">Tally</p>
      <p className="mt-1.5 tabular-nums text-osce-ink-700">
        <span className="font-semibold text-osce-success-text">G</span> {counts.G}{" "}
        <span className="font-semibold text-osce-warning-text">A</span> {counts.A}{" "}
        <span className="font-semibold text-osce-danger-text">R</span> {counts.R}{" "}
        <span className="text-osce-ink-500"> / {counts.total}</span>
      </p>
    </div>
  );
}

export function RagGradePreviewRow() {
  return (
    <div className="flex items-start gap-2">
      <div className="min-w-0 flex-1">
        <p className="text-osce-caption text-osce-ink-500">Score + comment on R/A</p>
      </div>
      <div className="flex shrink-0 gap-1">
        {(["R", "A", "G"] as const).map((g) => (
          <span
            key={g}
            className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-osce-canvas text-osce-caption font-bold text-osce-ink-500"
          >
            {g}
          </span>
        ))}
      </div>
    </div>
  );
}
