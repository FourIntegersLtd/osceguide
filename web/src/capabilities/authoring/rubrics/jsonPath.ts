/** JSON paths as the api writes them (`outline[0].competencies[1].label`), and immutable reads and writes by path. Pure. */

export const isJsonObject = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);

export type PathSegment = string | number;
export type JsonPath = readonly PathSegment[];

/** `["outline", 0, "id"]` as the backend writes it: `outline[0].id`. */
export function pathText(path: JsonPath): string {
  return path.reduce<string>((text, segment) => (typeof segment === "number" ? `${text}[${segment}]` : text === "" ? segment : `${text}.${segment}`), "");
}

/** The inverse of `pathText`. */
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
    for (const indexMatch of (indexes ?? "").matchAll(/\[(\d+)\]/g)) segments.push(Number(indexMatch[1]));
  }
  return segments;
}

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

/** A copy of `root` with `value` at `path`; `undefined` removes an object key. */
export function setAt<Root>(root: Root, path: JsonPath, value: unknown): Root {
  if (path.length === 0) return value as Root;
  const [head, ...rest] = path;
  if (typeof head === "number") {
    const list = Array.isArray(root) ? [...(root as unknown[])] : [];
    list[head] = setAt(list[head], rest, value);
    return list as Root;
  }
  const object: Record<string, unknown> = isJsonObject(root) ? { ...root } : {};
  const next = setAt(object[head as string], rest, value);
  if (next === undefined) delete object[head as string];
  else object[head as string] = next;
  return object as Root;
}
