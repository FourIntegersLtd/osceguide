/**
 * The temporary-password rule, for the screens that relay one by hand.
 *
 * Mirrors `validate_password` in api/app/features/identity/domain.py so the admin hears
 * "too weak" before submitting, not as a 422 afterwards. Keep the two in step.
 */
export const MIN_LENGTH = 12;

/** Why this would be refused, or null: also null while nothing is typed yet. */
export function temporaryPasswordIssue(raw: string): string | null {
  if (raw.length === 0) return null;
  if (raw.length < MIN_LENGTH) return `Use at least ${MIN_LENGTH} characters`;
  const classes = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^A-Za-z0-9]/].filter((pattern) => pattern.test(raw));
  if (classes.length < 2) return "Mix letters with numbers, punctuation, or capitals";
  return null;
}

// No i, l, o, 0, 1 where they would be misread when relayed by phone or message.
const LOWER = "abcdefghjkmnpqrstuvwxyz";
const UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ";
const DIGITS = "23456789";
const ALL = LOWER + UPPER + DIGITS;

/** 16 characters that always pass `temporaryPasswordIssue`; `bytes` is injectable for tests. */
export function generateTemporaryPassword(
  bytes: Uint8Array = crypto.getRandomValues(new Uint8Array(16)),
): string {
  return Array.from(bytes, (byte, index) => {
    const pool = index === 0 ? LOWER : index === 1 ? UPPER : index === 2 ? DIGITS : ALL;
    return pool[byte % pool.length];
  }).join("");
}
