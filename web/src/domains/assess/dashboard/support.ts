import type { LiveCircuit, OrgSittingRow } from "@/domains/assess/dashboard/api";
import type { ResultsIndexRow } from "@/domains/assess/results/api";
import { undecided } from "@/domains/assess/results/support";
import type { AssessWords } from "@/domains/assess/vocabulary";

/**
 * What the institution's home screen works out from what it is given.
 *
 * One request answers the setup flags, so a failed fetch cannot read as "you have no
 * trainees"; these are the judgements left over.
 */

/** "Formal exam" or "Training": the words for a sitting's mode. */
export function modeLabel(mode: string, w: AssessWords): string {
  return mode === "exam" ? w.formalExam : mode === "training" ? w.training : mode;
}

/** "2 circuits · 16 trainees": what a sitting holds; candidates for a formal exam. */
export function sittingTally(
  sitting: { mode: string; circuit_count: number; candidate_count: number },
  w: AssessWords,
): string {
  if (sitting.circuit_count === 0) return "No circuits yet";
  const circuits = `${sitting.circuit_count} ${sitting.circuit_count === 1 ? "circuit" : "circuits"}`;
  const one = sitting.mode === "exam" ? "candidate" : w.trainee;
  const many = sitting.mode === "exam" ? "candidates" : w.trainees;
  return `${circuits} · ${sitting.candidate_count} ${sitting.candidate_count === 1 ? one : many}`;
}

/** The sittings still to come, soonest first. */
export function comingUp(sittings: readonly OrgSittingRow[]): OrgSittingRow[] {
  return sittings
    .filter((sitting) => sitting.status === "scheduled")
    .sort((a, b) => (a.scheduled_for ?? "").localeCompare(b.scheduled_for ?? ""));
}

function decidable(row: ResultsIndexRow): boolean {
  return row.mode === "exam" && (row.status === "completed" || row.status === "reviewed");
}

/** People added but not yet joined: the server's count, one row that opens People. */
export function notJoinedItem(count: number, w: AssessWords): AttentionItem | null {
  if (count <= 0) return null;
  return {
    key: "not-joined",
    tag: `${count} not joined`,
    title:
      count === 1
        ? `A ${w.trainee} who has not accepted their invitation`
        : `${w.Trainees} who have not accepted their invitation`,
    body: "They cannot be scheduled until they set a password. Resend in one step.",
    href: "/people",
    tone: "neutral",
  };
}

export type AttentionItem = {
  key: string;
  tag: string;
  title: string;
  body: string;
  /** Surface-relative. */
  href: string;
  /** The tag chip's tone on the Today board. */
  tone?: "warn" | "ok" | "neutral";
};

/**
 * What needs the administrator, oldest first, from the results index: outcomes still to write
 * and signed-off results still to release, one row per sitting and kind. Only a formal exam
 * that has finished has decisions to write: a scheduled sitting's candidates are not waiting on
 * anyone and a training sitting never signs off.
 */
export function attentionFromResults(rows: readonly ResultsIndexRow[], w: AssessWords): AttentionItem[] {
  const items: AttentionItem[] = [];
  for (const row of rows.slice().reverse()) {
    const decisions = decidable(row) ? undecided(row) + row.draft : 0;
    if (decisions > 0) {
      const href = `/sittings/${row.sitting_id}/results`;
      items.push(
        w.hiring
          ? {
              key: `${row.sitting_id}-decide`,
              tag: "Decide",
              title: `${decisions} ${decisions === 1 ? `${w.trainee} needs` : `${w.trainees} need`} a hiring decision`,
              body: row.name,
              href,
            }
          : {
              key: `${row.sitting_id}-decide`,
              tag: `${decisions} ${decisions === 1 ? "decision" : "decisions"}`,
              title: `Record outcomes for ${row.name}`,
              body: `Write the outcome and reason for each person, then sign off.`,
              href,
              tone: "warn",
            },
      );
    }
    if (row.signed_off > 0) {
      items.push({
        key: `${row.sitting_id}-release`,
        tag: `${row.signed_off} ready`,
        title: `Release results for ${row.name}`,
        body: `Signed off. ${w.Trainees} see nothing until you release.`,
        href: `/sittings/${row.sitting_id}/results`,
        tone: "ok",
      });
    }
  }
  return items;
}

/* ------------------------------------------------------------------------
 * The exam-day board.
 * --------------------------------------------------------------------- */

/** Where one circuit is, in a phrase. */
export function circuitStatus(circuit: LiveCircuit): string {
  if (circuit.paused) return "Paused";
  if (circuit.phase === "break") return "Between stations";
  if (circuit.phase === "reading") return "Reading time";
  if (circuit.phase === "simulation") return "Consultation";
  return "Running";
}

/**
 * Whether a station is running with nothing recording it.
 *
 * The board carries the attempt so this is visible while it is happening
 * rather than discovered when somebody goes looking for a transcript.
 */
export function recordingMissing(circuit: LiveCircuit): boolean {
  if (circuit.phase !== "simulation") return false;
  if (!circuit.attempt_id) return true;
  return circuit.attempt_status === "failed";
}

/** Rows a human should look at first: trouble, then the clock. */
export function boardOrder(circuits: LiveCircuit[]): LiveCircuit[] {
  return circuits.slice().sort((a, b) => {
    const trouble = weight(b) - weight(a);
    if (trouble !== 0) return trouble;
    // Then whoever runs out of time first.
    const left = (a.remaining_seconds ?? Number.MAX_SAFE_INTEGER) -
      (b.remaining_seconds ?? Number.MAX_SAFE_INTEGER);
    if (left !== 0) return left;
    return a.circuit_name.localeCompare(b.circuit_name);
  });
}

function weight(circuit: LiveCircuit): number {
  let score = 0;
  if ((circuit.alerts ?? []).length > 0) score += 2;
  if (recordingMissing(circuit)) score += 2;
  if (circuit.paused) score += 1;
  return score;
}

export function candidatesLabel(circuit: LiveCircuit): string {
  const people = circuit.candidates ?? [];
  if (people.length === 0) return "Nobody on this circuit";
  const names = people.map((person) => person.name ?? person.email ?? "Candidate");
  if (names.length <= 2) return names.join(" and ");
  return `${names[0]}, ${names[1]} and ${names.length - 2} more`;
}

/* ---------- what ran earlier ---------- */

/**
 * Finished runs, newest first, under a heading per day.
 *
 * `/live/history` answers a flat page newest first, and the board reads it as
 * "this morning, yesterday, last Tuesday". Days are the browser's own, since
 * that is the clock the course lead reads them by.
 */
export function runsByDay<T extends { ended_at: string }>(
  runs: readonly T[],
  now: Date,
): { label: string; runs: T[] }[] {
  const dayKey = (date: Date) => `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
  const today = dayKey(now);
  const yesterday = dayKey(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1));
  const groups: { key: string; label: string; runs: T[] }[] = [];
  for (const run of runs) {
    const ended = new Date(run.ended_at);
    const key = dayKey(ended);
    let group = groups.find((item) => item.key === key);
    if (!group) {
      const label =
        key === today
          ? "Today"
          : key === yesterday
            ? "Yesterday"
            : ended.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
      group = { key, label, runs: [] };
      groups.push(group);
    }
    group.runs.push(run);
  }
  return groups.map(({ label, runs: items }) => ({ label, runs: items }));
}

/** "One circuit is running and five things need you." */
export function todaySentence(running: number, needs: number): string {
  const words = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
  const count = (n: number) => words[n] ?? String(n);
  const circuits = running === 1 ? "One circuit is running" : running === 0 ? "No circuit is running" : `${count(running)[0]?.toUpperCase()}${count(running).slice(1)} circuits are running`;
  const things = needs === 0 ? "nothing needs you" : `${count(needs)} ${needs === 1 ? "thing needs" : "things need"} you`;
  return `${circuits} and ${things}.`;
}

/** "Thursday 5 November": the eyebrow of the Today screen. */
export function dateEyebrow(now: Date): string {
  return now.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
}

/** The month and day of a sitting's date tile: "NOV", "12". */
export function dateTile(iso: string | null): { month: string; day: string } | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return {
    month: date.toLocaleDateString("en-GB", { month: "short" }).toUpperCase(),
    day: String(date.getDate()),
  };
}

/** "Thursday, 12 November, 09:30": a date with its time, for the next-circuit card. */
export function longWhen(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date
    .toLocaleString("en-GB", { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" })
    .replace(" at ", ", ");
}

/** "12 Nov": a date without the time, for a circuit row. */
export function shortDate(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

/**
 * What a running circuit is doing, in one line. A formal exam: "Station 4 of 8 · Supervisor: Dr Patel
 * · 8 candidates". An employer: "3 candidates on stations · Assessor: Dr Patel".
 */
export function runningLine(circuit: LiveCircuit, w: AssessWords): string {
  const count = (circuit.candidates ?? []).length;
  const who = circuit.supervisor?.name ?? circuit.supervisor?.email;
  const lead = who ? `${w.Supervisor}: ${who}` : null;
  const people = `${count} ${count === 1 ? w.trainee : w.trainees}`;
  const parts = w.hiring
    ? [`${people} on stations`, lead]
    : [
        circuit.stations_total > 0
          ? `Station ${(circuit.current_station?.slot_index ?? circuit.stations_completed) + 1} of ${circuit.stations_total}`
          : null,
        lead,
        people,
      ];
  return parts.filter(Boolean).join(" · ");
}

/** "5 of 8 candidates still to review". */
export function stillToReviewLine(unmarked: number, total: number, w: AssessWords): string {
  return `${unmarked} of ${total} ${total === 1 ? w.trainee : w.trainees} still to review`;
}

/** "2 drafts waiting to be completed". */
export function draftsWaitingLine(drafts: number): string {
  return `${drafts} ${drafts === 1 ? "draft" : "drafts"} waiting to be completed`;
}

/** A supervisor's circuits grouped by sitting: one row per sitting, "· 6 circuits" when several. */
export function circuitsBySitting<T extends { sitting_id: string; sitting_name: string; circuit_name: string }>(
  rows: readonly T[],
): { sittingId: string; title: string; rows: T[] }[] {
  const groups: { sittingId: string; title: string; rows: T[] }[] = [];
  for (const row of rows) {
    const found = groups.find((group) => group.sittingId === row.sitting_id);
    if (found) found.rows.push(row);
    else groups.push({ sittingId: row.sitting_id, title: row.sitting_name, rows: [row] });
  }
  return groups.map((group) => ({
    ...group,
    title:
      group.rows.length === 1
        ? `${group.title} · ${group.rows[0]?.circuit_name ?? ""}`
        : `${group.title} · ${group.rows.length} circuits`,
  }));
}

/** "Good afternoon, Dr Okafor": the Today board's greeting, the account's name as written (no usable name: just the greeting). */
export function todayGreeting(name: string | null | undefined, now: Date): string {
  const hour = now.getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const who = (name ?? "").trim();
  return who && !who.includes("@") ? `${greeting}, ${who}` : greeting;
}
