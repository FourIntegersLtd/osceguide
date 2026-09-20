/**
 * Active when the pathname is the link or a descendant of it.
 *
 * The shell root (e.g. `/staff`, `/app/me`) is exact-match only so Overview
 * does not stay highlighted on `/staff/team` or `/staff/authoring/...`.
 */
export function isNavActive(
  pathname: string,
  link: string,
  options?: { shellBase?: string },
): boolean {
  const target = link.split("?")[0];
  if (!target) return false;
  if (target === "/") return pathname === "/";

  const shellBase = options?.shellBase?.split("?")[0];
  if (shellBase && target === shellBase) {
    return pathname === target;
  }

  return pathname === target || pathname.startsWith(`${target}/`);
}
