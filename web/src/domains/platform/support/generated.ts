import { slugify } from "@/domains/platform/support/vocabulary";

const ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789";

function suffix(length = 4): string {
  const bytes = crypto.getRandomValues(new Uint8Array(length));
  return Array.from(bytes, (b) => ALPHABET[b % ALPHABET.length]).join("");
}

/**
 * A slug for a new organisation (api: `^[a-zA-Z0-9][a-zA-Z0-9-]*$`, 2 to 100).
 * The name alone first; `withSuffix` once that was taken. Staff never type it.
 */
export function slugCandidate(name: string, withSuffix: boolean): string {
  const base = slugify(name).slice(0, 90).replace(/-+$/, "") || "org";
  return withSuffix || base.length < 2 ? `${base}-${suffix()}` : base;
}

/**
 * A plan code (api: `^[a-z0-9][a-z0-9_]{1,22}$`; 23 so the `_referral` twin fits),
 * from the exam code and length, with a random suffix: codes are never reused.
 */
export function planCode(examCode: string, days: number): string {
  const months = Math.round(days / 30) || 1;
  const exam = examCode.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "plan";
  const tail = `_${months}m_${suffix()}`;
  return `${exam.slice(0, 23 - tail.length).replace(/_+$/, "") || "plan"}${tail}`.slice(0, 23);
}

/** Run `attempt` (0, 1, ...) again with a fresh code while `isConflict`, at most 3 retries. */
export async function retryOnConflict<T>(
  attempt: (n: number) => Promise<T>,
  isConflict: (cause: unknown) => boolean,
): Promise<T> {
  for (let n = 0; ; n++) {
    try {
      return await attempt(n);
    } catch (cause) {
      if (n >= 3 || !isConflict(cause)) throw cause;
    }
  }
}
