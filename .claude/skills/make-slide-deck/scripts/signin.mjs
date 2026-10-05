// signin.mjs <out.json> : sign in to the local platform-api as the seeded walkthrough account (example.com only).
import { writeFileSync } from "node:fs";
import { signInWithPassword } from "../../../../web/scripts/admin-totp.mjs";
const base = process.env.PLATFORM_API_URL ?? "http://localhost:8012";
const email = process.env.WALKTHROUGH_EMAIL ?? "walkthrough@example.com";
if (!email.endsWith("@example.com")) throw new Error("only @example.com accounts");
const s = await signInWithPassword(base, email, process.env.WALKTHROUGH_PASSWORD ?? "correct horse battery");
writeFileSync(process.argv[2], JSON.stringify(s));
