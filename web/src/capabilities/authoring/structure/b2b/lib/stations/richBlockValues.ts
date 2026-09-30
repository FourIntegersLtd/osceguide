import type { RecordField, StationBlockType } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

/** A grouped-list item: plain text, or a title with the reasons beneath it. */
export type GroupedItem = string | { title: string; reasons: string[] };
export type QaPair = { question: string; answer: string };

export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** A media item: a bare URL, or `{url, kind?, caption?, alt?}`. */
function isMediaItem(item: unknown): boolean {
  return typeof item === "string" || (isObject(item) && typeof item.url === "string");
}

function isGroupedItem(item: unknown): boolean {
  if (typeof item === "string") return true;
  return (
    isObject(item) &&
    typeof item.title === "string" &&
    (item.reasons === undefined ||
      (Array.isArray(item.reasons) && item.reasons.every((reason) => typeof reason === "string")))
  );
}

/** Mirrors `_RICH_SHAPES` in platform-api's `station_content.py`: each rich type's value shape and its error. */
export const RICH_SHAPES: Partial<Record<StationBlockType, { accepts: (value: unknown) => boolean; message: string }>> = {
  media: {
    accepts: (value) => isMediaItem(value) || (Array.isArray(value) && value.every(isMediaItem)),
    message: "Must be a media URL, a {url} object, or a list of them",
  },
  records: {
    accepts: (value) => Array.isArray(value) && value.every(isObject),
    message: "Must be a list of records",
  },
  qaList: {
    accepts: (value) =>
      Array.isArray(value) && value.every((pair) => isObject(pair) && typeof pair.question === "string"),
    message: "Must be a list of questions and answers",
  },
  groupedList: {
    accepts: (value) =>
      isObject(value) && Object.values(value).every((items) => Array.isArray(items) && items.every(isGroupedItem)),
    message: "Must be groups of items",
  },
};

/**
 * One group's items as text an author can type: an item per line, and a line
 * starting "- " is a reason under the item above it.
 */
export function groupedItemsToText(items: GroupedItem[]): string {
  return items
    .flatMap((item) =>
      typeof item === "string" ? [item] : [item.title, ...item.reasons.map((reason) => `- ${reason}`)],
    )
    .join("\n");
}

/** The reverse of `groupedItemsToText`; an item with no reasons stays plain text. */
export function groupedItemsFromText(text: string): GroupedItem[] {
  const items: { title: string; reasons: string[] }[] = [];
  for (const rawLine of text.split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    const previous = items[items.length - 1];
    if (line.startsWith("- ") && previous) {
      previous.reasons.push(line.slice(2).trim());
    } else {
      items.push({ title: line, reasons: [] });
    }
  }
  return items.map((item) => (item.reasons.length > 0 ? item : item.title));
}

/** A record column's stored key, from the label an author typed. */
export function columnKey(label: string): string {
  return label
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

/** Columns from one label per line; a column keeps its key while its position holds, so stored records still match. */
export function columnsFromLabels(labels: string[], previous: RecordField[]): RecordField[] {
  return labels.map((label, index) => ({
    key: previous[index]?.key || columnKey(label) || `column_${index + 1}`,
    label,
  }));
}
