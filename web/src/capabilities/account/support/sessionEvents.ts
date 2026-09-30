/**
 * Where it is safe to send somebody after they sign in.
 *
 * The retiring version of this file was mostly plumbing for an axios
 * interceptor — a session-expired event, a list of endpoints whose 401 is a
 * normal answer, a login path to redirect to. The platform client handles all
 * of that itself, so what is left is the one rule that still matters.
 */

/** Paths that never need a session, and so are never worth returning to. */
const PUBLIC_PREFIXES = ["/login", "/register", "/forgot-password", "/reset-password", "/change-password", "/compliances", "/exams", "/institutions", "/blogs"];

export function isPublicPath(pathname: string): boolean {
  if (pathname === "/") return true;
  return PUBLIC_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

/**
 * Only a same-origin absolute path is a safe return target.
 *
 * `//evil.example` is a protocol-relative URL that browsers treat as another
 * origin, so the leading-slash check alone is not enough — that is an open
 * redirect, and a sign-in page is exactly where one gets used.
 */
export function sanitizeReturnTo(value: string | null | undefined): string | null {
  if (!value) return null;
  if (!value.startsWith("/") || value.startsWith("//")) return null;
  const [path = value] = value.split("?");
  if (isPublicPath(path)) return null;
  return value;
}
