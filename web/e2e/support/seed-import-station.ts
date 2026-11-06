/**
 * Sample state of the ImportStation board (ImportStation.dc.html) for the exams org: the four "Recent imports" rows
 * (reading the file, template drafted but not published, draft station created, failed). Imports are background jobs
 * that call a model, so the finished rows are written by psql, as seed-home.ts does for run history. Test data only.
 */
import { call, orgPath } from "./api";
import { psql, q } from "./db";
import { communicationStructure, examsOrg, type ExamsOrg } from "./seed-exams";

export async function importStationOrg(): Promise<ExamsOrg> {
  const org = await examsOrg();
  const base = orgPath(org.slug, "/station-templates");
  const list = await call<{ items: { id: string; title: string; versions: { id: string }[] }[] }>(org.token, base);
  let draft = list.items.find((t) => t.title === "Bad news layout");
  if (!draft) {
    await call(org.token, base, { method: "POST", body: { title: "Bad news layout", exam_code: "finals", structure: communicationStructure() } });
    draft = (await call<{ items: { id: string; title: string; versions: { id: string }[] }[] }>(org.token, base)).items.find((t) => t.title === "Bad news layout");
  }
  if (!draft) throw new Error("draft template was not created");
  const orgId = psql(`select id from organizations where slug = ${q(org.slug)};`);
  const stationId = psql(`select id from stations where org_id = '${orgId}' order by created_at limit 1;`);
  const row = (name: string, status: string, ago: number, extra: { template?: boolean; station?: boolean; error?: string }) =>
    `insert into station_imports (id, owner_kind, org_id, exam_code, original_filename, extracted_text, status, template_id, template_version_id, station_id, review_notes, error, created_at, updated_at)
     values (gen_random_uuid(), 'org', '${orgId}', 'finals', ${q(name)}, 'text', ${q(status)},
       ${extra.template ? `'${draft!.id}'` : "null"}, ${extra.template ? `'${draft!.versions[0]?.id ?? ""}'` : "null"},
       ${extra.station && stationId ? `'${stationId}'` : "null"}, ${extra.station ? `'{"empty":[],"reworded":[]}'::jsonb` : "null"}, ${extra.error ? q(extra.error) : "null"},
       now() - interval '${ago} minutes', now() - interval '${ago} minutes');`;
  psql(`delete from station_imports where org_id = '${orgId}';
    ${row("scan.pdf", "failed", 4, {})}
    ${row("abdo-exam.pdf", "completed", 3, { station: true })}
    ${row("bad-news.docx", "template_ready", 2, { template: true })}
    ${row("chest-pain.pdf", "drafting_template", 1, {})}`);
  return org;
}
