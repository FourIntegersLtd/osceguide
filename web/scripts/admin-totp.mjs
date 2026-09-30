/**
 * RFC 6238 TOTP for a platform admin, with node:crypto only.
 *
 * The shared secret is ADMIN_TOTP_SECRET, from the environment or from
 * ~/.osce-staging-accounts.env (or ~/.osce-local-accounts.env). bootstrap_admin.py
 * confirms that secret on the admin account. Password sign-in then returns
 * mfa_required, and this module completes it.
 */
import { createHmac } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

function base32Decode(input) {
  const cleaned = input.replace(/=+$/g, "").replace(/ /g, "").toUpperCase();
  let bits = "";
  for (const character of cleaned) {
    const value = BASE32.indexOf(character);
    if (value < 0) throw new Error("ADMIN_TOTP_SECRET is not base32");
    bits += value.toString(2).padStart(5, "0");
  }
  const bytes = [];
  for (let index = 0; index + 8 <= bits.length; index += 8) {
    bytes.push(parseInt(bits.slice(index, index + 8), 2));
  }
  return Buffer.from(bytes);
}

/** Six-digit TOTP for `secret` at `nowMs` (30-second step, SHA-1). */
export function totp(secret, nowMs = Date.now()) {
  const counter = Math.floor(nowMs / 1000 / 30);
  const counterBytes = Buffer.alloc(8);
  counterBytes.writeBigUInt64BE(BigInt(counter));
  const mac = createHmac("sha1", base32Decode(secret)).update(counterBytes).digest();
  const offset = mac[mac.length - 1] & 0x0f;
  const binary =
    ((mac[offset] & 0x7f) << 24) |
    ((mac[offset + 1] & 0xff) << 16) |
    ((mac[offset + 2] & 0xff) << 8) |
    (mac[offset + 3] & 0xff);
  return String(binary % 1_000_000).padStart(6, "0");
}

export function adminTotpSecret() {
  const fromEnv = process.env.ADMIN_TOTP_SECRET?.trim();
  if (fromEnv) return fromEnv;
  for (const name of [".osce-staging-accounts.env", ".osce-local-accounts.env"]) {
    const path = join(homedir(), name);
    if (!existsSync(path)) continue;
    for (const line of readFileSync(path, "utf8").split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const splitAt = trimmed.indexOf("=");
      if (splitAt < 0 || trimmed.slice(0, splitAt) !== "ADMIN_TOTP_SECRET") continue;
      return trimmed
        .slice(splitAt + 1)
        .trim()
        .replace(/^["']|["']$/g, "");
    }
  }
  return "";
}

/**
 * Password sign-in, completing MFA when the account is a platform admin
 * (or anyone else already enrolled). Returns the token pair.
 */
export async function signInWithPassword(apiBase, email, password) {
  const response = await fetch(`${apiBase}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(`login ${response.status} ${body?.code ?? ""}`);
  }
  if (body.status === "mfa_enrolment_required") {
    throw new Error(
      "This account must enrol an authenticator. Set ADMIN_TOTP_SECRET and re-run bootstrap_admin.py.",
    );
  }
  if (body.status !== "mfa_required") return body;
  const secret = adminTotpSecret();
  if (!secret) throw new Error("ADMIN_TOTP_SECRET is not set");
  const verified = await fetch(`${apiBase}/api/v1/auth/mfa/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ challenge_token: body.challenge_token, code: totp(secret) }),
  });
  const session = await verified.json().catch(() => null);
  if (!verified.ok) throw new Error(`mfa verify ${verified.status} ${session?.code ?? ""}`);
  return session;
}
