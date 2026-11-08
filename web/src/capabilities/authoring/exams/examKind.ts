import type { AssessWords } from "@/capabilities/assess-words/vocabulary";

/** What the row needs of an assessment: which exam it is for, how it was run and when. */
interface KindSitting {
  programme_id?: string | null;
  mode: string;
  scheduled_for?: string | null;
}

/**
 * "Formal exam" or "Training": the mode of the exam's most recent assessment. The api keeps mode on
 * the assessment, so an exam nobody has scheduled has no kind to show (null).
 */
export function examKind(
  examId: string,
  programmes: { id: string; exam_id: string }[],
  sittings: KindSitting[],
): "Formal exam" | "Training" | null {
  const programme = programmes.find((p) => p.exam_id === examId);
  if (!programme) return null;
  let latest: KindSitting | null = null;
  for (const sitting of sittings) {
    if (sitting.programme_id !== programme.id) continue;
    if (!latest || (sitting.scheduled_for ?? "") >= (latest.scheduled_for ?? "")) latest = sitting;
  }
  if (!latest) return null;
  return latest.mode === "exam" ? "Formal exam" : "Training";
}

/** An employer's exam row leads with its kind, as the board writes it; an institution's row is unchanged. */
export function examMetaWithKind(meta: string, kind: string | null, w: AssessWords): string {
  return w.hiring && kind ? `${kind} · ${meta}` : meta;
}

/** Every item of a cursor-paged list, so a long history is not cut at the first page. */
export async function collectPages<T>(
  fetchPage: (cursor: string | undefined) => Promise<{ items: T[]; next_cursor?: string | null }>,
): Promise<T[]> {
  const items: T[] = [];
  let cursor: string | undefined;
  do {
    const page = await fetchPage(cursor);
    items.push(...page.items);
    cursor = page.next_cursor ?? undefined;
  } while (cursor);
  return items;
}
