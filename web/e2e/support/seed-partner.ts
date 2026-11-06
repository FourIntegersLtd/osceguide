/**
 * Seeds the sample state of the Partner board (docs/institution-overhaul/boards/Partner.dc.html): a partner
 * organisation "Northern Deanery" whose links were opened 1,240 times by 980 people this month (62% SCA, 30% PLAB,
 * 8% ortho), with 86 sign-ups. Arrivals and acquisitions are written to the local database, the way the
 * arrival route and sign-up would; there is no api route that makes history. Paid (21 on the board) needs
 * payments for 21 real users and is left out: a named exception in the spec.
 */
import { createOrg } from "./api";
import { psql, q } from "./db";

export async function seedPartnerOrg(): Promise<{ slug: string; account: { email: string; password: string } }> {
  const { slug, account } = await createOrg({ prefix: "partner", role: "partner_admin", adminName: "Pia Partner", orgType: "partner", orgName: "Northern Deanery" });
  psql(`
    INSERT INTO partner_arrivals (id, partner, exam_code, visitor_key, ref_id, landing_path, landed_at, created_at, updated_at)
    SELECT gen_random_uuid(), ${q(slug)},
      CASE WHEN i % 100 < 62 THEN 'sca' WHEN i % 100 < 92 THEN 'plab' ELSE 'ortho' END,
      'v' || (i % 980), 'ndeanery-sca-spring', '/sca',
      date_trunc('month', now()) + (CASE WHEN i % 257 < 30 THEN 0 WHEN i % 257 < 85 THEN 1 WHEN i % 257 < 125 THEN 2 WHEN i % 257 < 195 THEN 3 ELSE 4 END || ' days')::interval + interval '9 hours', now(), now()
    FROM generate_series(1, 1240) AS i;
    INSERT INTO acquisitions (id, user_id, partner, exam_code, acquired_at, created_at, updated_at)
    SELECT gen_random_uuid(), id, ${q(slug)}, 'sca', date_trunc('month', now()) + ((CASE WHEN n <= 10 THEN 0 WHEN n <= 28 THEN 1 WHEN n <= 41 THEN 2 WHEN n <= 64 THEN 3 ELSE 4 END) || ' days')::interval + interval '10 hours', now(), now()
    FROM (SELECT id, row_number() OVER () AS n FROM users WHERE id NOT IN (SELECT user_id FROM acquisitions) LIMIT 86) u;
  `);
  return { slug, account };
}
