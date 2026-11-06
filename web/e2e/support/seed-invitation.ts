/**
 * A real invitation for the Accept invitation board (docs/institution-overhaul/boards/AcceptInvite.dc.html): the
 * organisation adds a person who has no account, the api queues the invitation email, and its token is read from
 * the outbox (the one database seam the other specs use, db.ts). The address uses the reserved example.com domain.
 */
import { call, orgPath, stamp } from "./api";
import { psql, q } from "./db";
import type { PeopleOrg } from "./seed-people";

export async function seedInvitationToken(org: PeopleOrg): Promise<string> {
  const email = `invited-${stamp()}@example.com`;
  await call(org.token, orgPath(org.slug, `/trainees`), { method: "POST", body: { email, first_name: "Amara", last_name: "Okoye" } });
  const token = psql(`SELECT payload->>'token' FROM outbound_messages WHERE recipient = ${q(email)} AND payload ? 'token' ORDER BY created_at DESC LIMIT 1;`).trim();
  if (!token) throw new Error(`no invitation token queued for ${email}`);
  return token;
}
