import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { askQuestion, listQuestions } from "@/capabilities/community/api";

const realFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = realFetch;
});

interface Call {
  url: string;
  method: string;
  body: Record<string, unknown> | undefined;
}

function record(body: unknown): Call[] {
  const calls: Call[] = [];
  globalThis.fetch = (async (input: unknown, init?: RequestInit) => {
    calls.push({
      url: String(input),
      method: init?.method ?? "GET",
      body: init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined,
    });
    return new Response(JSON.stringify(body), {
      status: 201,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;
  return calls;
}

const created = {
  id: "9f0e0f2a-2a4a-4c2b-9d37-5f1f5c0b6a11",
  kind: "question",
  title: "When do I escalate chest pain?",
  body: "When do I escalate chest pain?",
  author_id: "a1",
  author_name: "Ada",
  audience: { visibility: "public", org_id: null, group_id: null },
  created_at: "2026-09-24T09:00:00Z",
  like_count: 0,
  liked_by_me: false,
  parent_id: null,
  reply_count: 0,
  tags: ["cardiology"],
};

describe("asking a question", () => {
  it("sends the chosen specialty tags, which the feed and filter read back", async () => {
    // The tags existed on the backend since migration k2l3m4n5o6p7 and the
    // web wired none of them: the composer posted without the field and the
    // list rendered no chips, so the retiring client's discovery facet was
    // gone. This is the write half of that facet.
    const calls = record(created);
    await askQuestion({
      title: created.title,
      body: created.body,
      tags: ["cardiology", "acute_medicine"],
    });

    assert.equal(calls.length, 1);
    assert.ok(calls[0]?.url.endsWith("/api/v1/community/questions"));
    assert.equal(calls[0]?.method, "POST");
    assert.deepEqual(calls[0]?.body?.tags, ["cardiology", "acute_medicine"]);
  });

  it("sends an empty list when nothing is tagged, so the shape never moves", async () => {
    const calls = record(created);
    await askQuestion({ title: created.title, body: created.body });

    assert.deepEqual(calls[0]?.body?.tags, []);
  });
});

describe("listing questions", () => {
  it("asks the server to narrow the feed to one tag", async () => {
    const calls = record({ items: [], next_cursor: null });
    await listQuestions({ tag: "cardiology" });

    assert.equal(calls.length, 1);
    assert.match(calls[0]?.url ?? "", /\/api\/v1\/community\/questions\?/);
    assert.match(calls[0]?.url ?? "", /(?:^|[?&])tag=cardiology(?:&|$)/);
    assert.equal(calls[0]?.method, "GET");
  });

  it("does not send a tag when the feed is unfiltered", async () => {
    const calls = record({ items: [], next_cursor: null });
    await listQuestions({});

    assert.equal((calls[0]?.url ?? "").includes("tag="), false);
  });
});

describe("listQuestions exam filter", () => {
  it("sends the exam code as exam_code", async () => {
    const calls = record({ items: [], next_cursor: null });
    await listQuestions({ examCode: "sca" });
    assert.match(calls[0]?.url ?? "", /exam_code=sca/);
  });

  it("sends nothing when there is no exam", async () => {
    const calls = record({ items: [], next_cursor: null });
    await listQuestions({});
    assert.doesNotMatch(calls[0]?.url ?? "", /exam_code/);
  });
});
