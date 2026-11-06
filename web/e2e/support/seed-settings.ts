/**
 * Seeds the sample state of the Settings, Reporting and Invoices boards (docs/institution-overhaul/boards/) through
 * existing api routes. The signed-in owner and organisation come from seed-people.ts ("St Mary's Medical School",
 * example.com addresses only). Invoice numbers and dates are not the api's to choose (they come from a sequence and
 * the clock), so the board's are written with the one database seam the other specs use (db.ts); the amounts, lines,
 * statuses and PO numbers go through the routes.
 */
import { ADMIN, call, login, orgPath } from "./api";
import { psql, q } from "./db";
import { publishedExam, rubric } from "./seed-exams";
import type { PeopleOrg } from "./seed-people";

/** The Provisioning tab's two sample connectors: one live, one revoked. */
export async function seedScimTokens(org: PeopleOrg): Promise<void> {
  await call(org.token, orgPath(org.slug, `/scim/tokens`), { method: "POST", body: { label: "Okta trial" } });
  const list = await call<{ id: string; label: string }[]>(org.token, orgPath(org.slug, `/scim/tokens`));
  const okta = list.find((t) => t.label === "Okta trial");
  if (okta) await call(org.token, orgPath(org.slug, `/scim/tokens/${okta.id}`), { method: "DELETE" });
  await call(org.token, orgPath(org.slug, `/scim/tokens`), { method: "POST", body: { label: "Entra ID" } });
}

/**
 * The board's invoice numbers are four digits (INV-2026-0142). The api numbers its own with six
 * (`INV-<year>-<sequence:06d>`, billing/domain.py invoice_number), so a board number can never equal
 * one the sequence hands out, whatever the database holds; the unique constraint is only ever met by an earlier run's.
 */
const BOARD_NUMBER = /^INV-\d{4}-\d{4}$/;

const BOARD_INVOICES = [
  { number: "INV-2026-0142", issued: "2026-11-01", due: "2026-12-01", status: "issued", po: "PO-88231", lines: [["Institution plan, Nov 2026 to Jan 2027", 400000], ["VAT 20%", 80000]] },
  { number: "INV-2026-0098", issued: "2026-08-01", due: "2026-08-31", status: "paid", po: "PO-77410", lines: [["Institution plan, Aug 2026 to Oct 2026", 400000], ["VAT 20%", 80000]] },
  { number: "INV-2026-0051", issued: "2026-05-01", due: "2026-05-31", status: "void", po: null, lines: [["Institution plan, May 2026", 100000], ["VAT 20%", 20000]] },
] as const;

/** The Invoices board's three invoices, oldest raised first so the newest issued date lists first. */
export async function seedInvoices(org: PeopleOrg): Promise<void> {
  const platform = await login(ADMIN.email, ADMIN.password);
  for (const inv of [...BOARD_INVOICES].reverse()) {
    if (!BOARD_NUMBER.test(inv.number)) throw new Error(`board invoice number ${inv.number} is not in the board's own four-digit range`);
    const made = await call<{ id: string }>(platform, `/api/v1/platform/organizations/${org.slug}/invoices`, {
      method: "POST",
      body: {
        po_number: inv.po ?? undefined,
        notes: inv.number === "INV-2026-0142" ? "Termly billing." : undefined,
        lines: inv.lines.map(([description, unit]) => ({ description, quantity: 1, unit_amount_pence: unit })),
      },
    });
    if (inv.status !== "issued") await call(platform, `/api/v1/platform/invoices/${made.id}`, { method: "PATCH", body: { status: inv.status } });
    // Named exception: the number and dates are not settable through a route.
    // The number is unique across the database: a previous run's invoice gives it up.
    psql(`UPDATE invoices SET invoice_number = 'OLD-' || substr(id::text, 1, 8) WHERE invoice_number = ${q(inv.number)};`);
    psql(`UPDATE invoices SET invoice_number = ${q(inv.number)}, issued_at = ${q(`${inv.issued} 09:00+00`)}, due_at = ${q(`${inv.due} 09:00+00`)} WHERE id = ${q(made.id)};`);
  }
}

/** The Reporting board's three exams, in its order, with the sittings it counts (4, 2 and 6). */
export async function seedReportingExams(org: PeopleOrg): Promise<void> {
  const { slug, token } = org;
  const scheme = await rubric(token, slug, "Consultation skills", 1, 0);
  const versionId = scheme.versions[0]?.id;
  for (const [code, name, sittings] of [["finals", "Final-year OSCE", 4], ["year4", "Year 4 mock", 2], ["year3", "Year 3 practice", 6]] as const) {
    const { programmeId } = await publishedExam(token, slug, { code, name, versionId });
    for (let n = 1; n <= sittings; n += 1) {
      await call(token, orgPath(slug, `/sittings`), {
        method: "POST",
        body: { name: `${name} ${n}`, mode: "exam", sitting_type: "mock_exam", programme_id: programmeId, scheduled_for: null },
      });
    }
  }
}
