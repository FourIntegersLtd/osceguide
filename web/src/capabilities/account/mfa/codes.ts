/**
 * The small text rules the two-factor screens share, kept out of components.
 */

/**
 * An authenticator code as typed, reduced to what the server compares.
 *
 * Apps show "123 456" and people paste it that way; the server takes six
 * digits. Anything that is not a digit is dropped rather than refused, so a
 * pasted space or dash is not a failed attempt against the rate limit.
 */
export function normaliseTotp(input: string): string {
  return input.replace(/\D/g, "");
}

/** Six digits, which is what every authenticator app shows for this issuer. */
export function isCompleteTotp(input: string): boolean {
  return /^\d{6}$/.test(normaliseTotp(input));
}

/**
 * A recovery code as typed. Case and spacing are the person's; the code is
 * the server's, so only surrounding whitespace is trimmed.
 */
export function normaliseRecoveryCode(input: string): string {
  return input.trim();
}

/**
 * The shared secret in groups of four, for typing into an app by hand.
 *
 * A base32 secret is 32 characters of capitals and digits; read in one run it
 * is easy to lose your place halfway through.
 */
export function groupSecret(secret: string): string {
  return (secret.replace(/\s+/g, "").match(/.{1,4}/g) ?? []).join(" ");
}

/** The recovery codes as a text file someone can keep. */
export function recoveryCodesFile(codes: readonly string[], issuedAt: Date): string {
  return [
    "OSCE Guide recovery codes",
    `Issued ${issuedAt.toISOString().slice(0, 10)}. Each code works once.`,
    "",
    ...codes,
    "",
  ].join("\n");
}
