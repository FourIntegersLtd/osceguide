/**
 * Every item of a cursor-paged list, walked to the end.
 *
 * For the callers that need the complete set (a picker, a lookup) rather than a display page.
 * It does not stop at some page count: a silent stop hid items from the picker.
 */
export async function collectPages<T>(
  fetchPage: (cursor: string | null) => Promise<{ items: T[]; next_cursor?: string | null }>,
): Promise<T[]> {
  const items: T[] = [];
  let cursor: string | null = null;
  do {
    const page: { items: T[]; next_cursor?: string | null } = await fetchPage(cursor);
    items.push(...page.items);
    cursor = page.next_cursor ?? null;
  } while (cursor);
  return items;
}
