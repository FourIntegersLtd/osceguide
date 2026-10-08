/**
 * Every item of a cursor-paged list, walked to the end.
 *
 * For the callers that need the complete set (a picker, a lookup) rather than a display page.
 * It never stops quietly short: a silent stop hid items from the picker. A server that keeps
 * returning a cursor past a generous cap is a fault, so that throws.
 */
const MAX_PAGES = 1000;

export async function collectPages<T>(
  fetchPage: (cursor: string | null) => Promise<{ items: T[]; next_cursor?: string | null }>,
): Promise<T[]> {
  const items: T[] = [];
  let cursor: string | null = null;
  for (let walked = 0; ; walked += 1) {
    if (walked >= MAX_PAGES) throw new Error(`Still more pages after ${MAX_PAGES}; refusing to keep walking.`);
    const page: { items: T[]; next_cursor?: string | null } = await fetchPage(cursor);
    items.push(...page.items);
    cursor = page.next_cursor ?? null;
    if (!cursor) break;
  }
  return items;
}
