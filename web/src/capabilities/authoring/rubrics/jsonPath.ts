/**
 * Reading and writing a rubric structure by path, without losing anything.
 *
 * The builder edits the structure the backend stores as plain JSON rather than
 * copying it into a typed model and back. A copied platform rubric carries
 * keys no form here edits (`basedOn`, a field's `example` or `default`, a
 * nullable domain's `description`), and a round trip through a narrower type
 * would silently drop them. So every edit is "set this value at this path" on
 * the original object, and everything else is kept as it was.
 *
 * Paths are written the way the backend writes a problem's path
 * (`sections[0].competencies[1].id`), so an input and the problem that names
 * it compare as plain strings.
 */

export type JsonObject = Record<string, unknown>;
export type PathSegment = string | number;
export type JsonPath = readonly PathSegment[];

export function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** `["sections", 0, "id"]` as the backend writes it: `sections[0].id`. */
export function pathText(path: JsonPath): string {
  return path.reduce<string>((text, segment) => {
    if (typeof segment === "number") return `${text}[${segment}]`;
    return text === "" ? segment : `${text}.${segment}`;
  }, "");
}

/** The inverse of `pathText`: `sections[0].id` is `["sections", 0, "id"]`. */
export function parsePath(text: string): PathSegment[] {
  const segments: PathSegment[] = [];
  for (const part of text.split(".")) {
    if (part === "") continue;
    const match = /^([^[\]]*)((?:\[\d+\])*)$/.exec(part);
    if (!match) {
      segments.push(part);
      continue;
    }
    const [, name, indexes] = match;
    if (name) segments.push(name);
    for (const indexMatch of (indexes ?? "").matchAll(/\[(\d+)\]/g)) {
      segments.push(Number(indexMatch[1]));
    }
  }
  return segments;
}

/** The value at `path`, or undefined when any step along it is missing. */
export function getAt(root: unknown, path: JsonPath): unknown {
  let current: unknown = root;
  for (const segment of path) {
    if (typeof segment === "number") {
      if (!Array.isArray(current)) return undefined;
      current = current[segment];
    } else {
      if (!isJsonObject(current)) return undefined;
      current = current[segment];
    }
  }
  return current;
}

/**
 * A copy of `root` with `value` at `path`; every object and list on the way
 * is copied, nothing else is. `undefined` removes an object key, which is how
 * an optional setting goes back to "use the default".
 */
export function setAt<Root>(root: Root, path: JsonPath, value: unknown): Root {
  if (path.length === 0) return value as Root;
  const [head, ...rest] = path;
  if (typeof head === "number") {
    const list = Array.isArray(root) ? [...(root as unknown[])] : [];
    list[head] = setAt(list[head], rest, value);
    return list as Root;
  }
  const object: JsonObject = isJsonObject(root) ? { ...root } : {};
  const next = setAt(object[head as string], rest, value);
  if (next === undefined) delete object[head as string];
  else object[head as string] = next;
  return object as Root;
}

/** The list at `path` (empty when there is none yet). */
export function listAt(root: unknown, path: JsonPath): unknown[] {
  const value = getAt(root, path);
  return Array.isArray(value) ? value : [];
}

/** A copy of `root` with the list at `path` replaced by `change(list)`. */
export function updateList<Root>(root: Root, path: JsonPath, change: (list: unknown[]) => unknown[]): Root {
  return setAt(root, path, change([...listAt(root, path)]));
}

/** A copy of `root` without the list item at `path` (whose last segment is its index). */
export function removeItem<Root>(root: Root, path: JsonPath): Root {
  const index = path[path.length - 1];
  if (typeof index !== "number") return setAt(root, path, undefined);
  return updateList(root, path.slice(0, -1), (list) => list.filter((_, position) => position !== index));
}

/** A copy of `root` with the list item at `path` moved `offset` places, when there is room. */
export function moveItem<Root>(root: Root, path: JsonPath, offset: number): Root {
  const index = path[path.length - 1];
  if (typeof index !== "number") return root;
  return updateList(root, path.slice(0, -1), (list) => {
    const target = index + offset;
    if (target < 0 || target >= list.length) return list;
    const [moved] = list.splice(index, 1);
    list.splice(target, 0, moved);
    return list;
  });
}
