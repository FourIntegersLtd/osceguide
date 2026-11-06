/**
 * Seeds the Slot review board's tab 1 state on the Results org (docs/institution-overhaul/boards/SlotReview.dc.html):
 * Amara Okoye's station 2 is marked, the admin has completed a review of it, and the supervisor Dr Patel has a
 * draft with two of the three required areas rated ("1 completed review · 1 still in progress", "Still to rate
 * before completing: Clinical reasoning").
 */
import { call } from "./api";
import { psql } from "./db";
import { seedResultsOrg, type ResultsOrg, type SlotRow } from "./seed-results";

interface FormField { path: string; domain_id: string }
interface ReviewsRead { form: { fields: FormField[] } | null }

export interface SlotReviewOrg extends ResultsOrg {
  /** Amara Okoye, station 2: the slot the board shows. */
  slot: SlotRow;
  /** Dr Patel, the circuit's supervisor and the board's reviewer. */
  supervisor: { email: string; password: string };
  /** Hugo Stone's station 1: taken, no AI mark yet ("Marking" state). */
  pending: SlotRow;
  /** His station 2: the scorer gave up ("Could not be marked" state). */
  failed: SlotRow;
  /** Dev Shah's station 1: Dr Patel and Ms Clarke both finished, and agree. */
  agreed: SlotRow;
}

export async function seedSlotReviewOrg(): Promise<SlotReviewOrg> {
  const org = await seedResultsOrg();
  const slot = org.marchSlots.find((s) => s.candidate === 0 && s.index === 1);
  const supervisor = org.staffAccounts["Dr Patel"];
  if (!slot || !supervisor) throw new Error("no Amara station 2 slot or Dr Patel");
  const base = `/api/v1/orgs/${org.slug}/slots/${slot.slotId}/reviews`;
  const { form } = await call<ReviewsRead>(org.token, base);
  const fields = form?.fields ?? [];
  if (fields.length < 3) throw new Error("the slot's review form has fewer than three fields");
  const ratings = (count: number, value: string) => JSON.stringify(Object.fromEntries(fields.slice(0, count).map((field) => [field.path, value])));
  // Amara is already signed off, which the review routes refuse to change, so the two rows are written directly
  // (local database only, as seed-results does for the marking itself).
  const row = (email: string, status: "draft" | "completed", values: string) => `
INSERT INTO slot_reviews (id, slot_id, org_id, submitted_by, status, field_values, completed_at)
  SELECT gen_random_uuid(), '${slot.slotId}', sl.org_id, u.id, '${status}', '${values}'::jsonb, ${status === "completed" ? "now()" : "NULL"}
  FROM slots sl, users u WHERE sl.id = '${slot.slotId}' AND u.email = '${email}';`;
  // The board's machine marks for Amara's station: Green, Amber, Green (the shared fixture gives Green for all three here).
  psql(`UPDATE assessment_results SET payload = jsonb_set(payload, '{domain_2,score}', '"A"') WHERE attempt_id = '${slot.attemptId}';`);
  psql(row(org.account.email, "completed", ratings(fields.length, "G")) + row(supervisor.email, "draft", ratings(2, "G")));
  // Tab 2: the admin's own review of the same station, a draft at revision 2 with every area rated Green and no overall.
  psql(`
INSERT INTO gp_lead_reviews (id, slot_id, org_id, revision, status, field_values, reviewed_by)
  SELECT gen_random_uuid(), '${slot.slotId}', sl.org_id, 2, 'draft', '${ratings(fields.length, "G")}'::jsonb, u.id
  FROM slots sl, users u WHERE sl.id = '${slot.slotId}' AND u.email = '${org.account.email}';`);
  // Tab 3: an unmarked taken station, and one whose marking gave up.
  const pick = (candidate: number, index: number): SlotRow => {
    const found = org.marchSlots.find((s) => s.candidate === candidate && s.index === index);
    if (!found) throw new Error(`no slot ${candidate}/${index}`);
    return found;
  };
  const pending = pick(7, 0);
  const failed = pick(7, 1);
  psql(`UPDATE attempts SET failed_reason = 'scoring_failed' WHERE id = '${failed.attemptId}';`);
  // Tab 4: two finished reviews that agree.
  const agreed = pick(3, 0);
  const both = (email: string) => `
INSERT INTO slot_reviews (id, slot_id, org_id, submitted_by, status, field_values, completed_at)
  SELECT gen_random_uuid(), '${agreed.slotId}', sl.org_id, u.id, 'completed', '${ratings(fields.length, "G")}'::jsonb, now()
  FROM slots sl, users u WHERE sl.id = '${agreed.slotId}' AND u.email = '${email}';`;
  psql(both(supervisor.email) + both(org.account.email));
  return { ...org, slot, supervisor, pending, failed, agreed };
}
