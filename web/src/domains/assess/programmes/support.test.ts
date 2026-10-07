import assert from "node:assert/strict";
import { afterEach, it } from "node:test";
import { importPlatformExam, listPlatformCatalogue } from "@/domains/assess/programmes/api";
import { adoptRefusal } from "@/domains/assess/programmes/support";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

function answer(status: number, body: unknown): typeof fetch {
  return async () => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

// B-4: the platform-exam catalogue and import routes had no caller, so an
// organisation could not adopt a published exam at all.
it("an organisation reads the platform's exams and adopting one already run says so", async () => {
  const calls: string[] = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push(`${init?.method ?? "GET"} ${new URL(String(input)).pathname} ${init?.body ?? ""}`);
    if (init?.method === "POST") {
      return answer(409, { code: "exam_already_imported", message: "already" })(input, init);
    }
    return answer(200, { items: [{ exam_id: "e1", code: "MRCGP", title: "MRCGP SCA", station_count: 12, already_imported: true }] })(input, init);
  }) as typeof fetch;

  const catalogue = await listPlatformCatalogue("acme");
  assert.equal(catalogue.items[0]?.title, "MRCGP SCA");
  const refused = await importPlatformExam("acme", "e1").then(() => null, (cause: unknown) => cause);
  assert.equal(adoptRefusal(refused), "Your organisation already runs that exam. It is in your programmes below.");
  assert.deepEqual(calls, ["GET /api/v1/orgs/acme/exams/catalog ", 'POST /api/v1/orgs/acme/exams/import {"platform_exam_id":"e1"}']);
});

it("a refusal for an exam the platform no longer offers says the list was refreshed", async () => {
  globalThis.fetch = answer(404, { code: "unknown_exam", message: "gone" });
  const refused = await importPlatformExam("acme", "e1").then(() => null, (cause: unknown) => cause);
  assert.equal(adoptRefusal(refused), "The platform no longer offers that exam. The list has been refreshed.");
});
