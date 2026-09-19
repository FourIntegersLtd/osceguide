/**
 * Walk the calls each screen makes, against a running platform-api.
 *
 * Not a unit test: it is the check that the client and the backend still agree
 * about routes, shapes and permission names. Those three are exactly what a
 * typed client cannot catch on its own, because the types come from a document
 * that can itself be stale — the capability keys in this repo were wrong for a
 * day for that reason.
 *
 *   node scripts/smoke.mjs [--email ...] [--password ...]
 */
const API = process.env.PLATFORM_API_URL ?? "http://127.0.0.1:8002";

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
}

let token = null;
const results = [];

async function step(label, path, { method = "GET", body, expect } = {}) {
  try {
    const response = await fetch(`${API}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await response.text();
    const payload = text ? JSON.parse(text) : null;
    if (!response.ok) throw new Error(`${response.status} ${payload?.code ?? ""}`);
    if (expect) expect(payload);
    results.push({ label, ok: true });
    return payload;
  } catch (error) {
    results.push({ label, ok: false, detail: error.message });
    return null;
  }
}

function must(condition, message) {
  if (!condition) throw new Error(message);
}

async function main() {
  const email = arg("email", "dev@example.com");
  const password = arg("password", "platform-dev-password-1");

  await step("health", "/health", { expect: (p) => must(p.status === "ok", "not ok") });

  const auth = await step("sign in", "/api/v1/auth/login", {
    method: "POST",
    body: { email, password },
    expect: (p) => must(p.access_token && p.refresh_token, "missing tokens"),
  });
  if (!auth) return report();
  token = auth.access_token;

  await step("who am I", "/api/v1/me", {
    expect: (p) => must(typeof p.email === "string", "no email"),
  });

  // The permission names the shells and guards branch on. A rename here
  // silently hides screens, so they are asserted by name.
  await step("my capabilities", "/api/v1/me/capabilities", {
    expect: (p) => {
      must(p.can && typeof p.can === "object", "no can map");
      for (const key of ["read_org", "manage_team", "run_circuits", "sign_off_results", "administer_platform"]) {
        must(key in p.can, `capability key missing: ${key}`);
      }
    },
  });

  await step("learner dashboard", "/api/v1/me/dashboard", {
    expect: (p) => must("entitlements" in p && "sets" in p, "unexpected shape"),
  });

  await step("exams", "/api/v1/exams", {
    expect: (p) => must(Array.isArray(p.items) && p.items.length > 0, "no exams seeded"),
  });

  await step("station library", "/api/v1/stations?limit=5", {
    expect: (p) => must(Array.isArray(p.items), "not a page"),
  });

  // The capability institutions asked for. Both surfaces render from this.
  await step("study material", "/api/v1/media?limit=10", {
    expect: (p) => must(Array.isArray(p.items), "not a page"),
  });

  const media = await step("study material kinds", "/api/v1/media?kind=slide_deck&limit=5", {
    expect: (p) => must(Array.isArray(p.items), "kind filter rejected"),
  });
  if (media?.items?.[0]) {
    await step("read one deck", `/api/v1/media/${media.items[0].slug}`, {
      expect: (p) => must(p.content !== undefined, "no content"),
    });
  }

  await step("my station sets", "/api/v1/me/station-sets");
  await step("my sittings", "/api/v1/me/sittings", {
    expect: (p) => must(Array.isArray(p.items), "not a list"),
  });
  await step("discussion", "/api/v1/community/questions?limit=5", {
    expect: (p) => must(Array.isArray(p.items), "not a page"),
  });
  await step("stream ticket", "/api/v1/auth/stream-ticket", {
    method: "POST",
    expect: (p) => must(typeof p.ticket === "string", "no ticket"),
  });
  await step("plans", "/api/v1/billing/plans");

  // The whole voice path short of the worker answering: an attempt is created
  // and frozen, then `voice` mints a room token and decides Cloud or
  // self-hosted. If this fails with `voice_unavailable`, the API has no
  // LIVEKIT_* credentials — see README, "Talking to the workers".
  const library = await step("library for an attempt", "/api/v1/stations?limit=1");
  const versionId = library?.items?.[0]?.version_id;
  if (versionId) {
    const attempt = await step("create an attempt", "/api/v1/attempts", {
      method: "POST",
      body: { exam_code: library.items[0].exam_code, kind: "practice", station_version_id: versionId },
      expect: (p) => must(p.id, "no attempt id"),
    });
    if (attempt) {
      await step("mint a voice token", `/api/v1/attempts/${attempt.id}/voice-token`, {
        method: "POST",
        expect: (p) => {
          must(typeof p.token === "string" && p.token.length > 100, "no LiveKit token");
          must(p.server_url?.startsWith("ws"), "no LiveKit server url");
          must(p.room, "no room name");
        },
      });
      // Leave nothing running: an abandoned attempt is the honest end state for
      // one nobody sat.
      await step("abandon it", `/api/v1/attempts/${attempt.id}/abandon`, { method: "POST" });
    }
  }

  // The institution path, when the demo organisation exists. Skipped rather
  // than failed otherwise, so this stays runnable on a bare database.
  const me = await step("my memberships", "/api/v1/me");
  const membership = (me?.memberships ?? [])[0];
  if (membership) {
    const switched = await step("switch workspace", "/api/v1/auth/switch-workspace", {
      method: "POST",
      body: { org_slug: membership.org_slug },
      expect: (p) => must(p.access_token, "no token"),
    });
    if (switched) token = switched.access_token;

    const slug = membership.org_slug;
    await step("org dashboard", `/api/v1/orgs/${slug}/dashboard`, {
      expect: (p) => must(p.counts && p.setup, "unexpected shape"),
    });
    await step("org trainees", `/api/v1/orgs/${slug}/trainees`);
    const sittings = await step("org sittings", `/api/v1/orgs/${slug}/sittings`);
    const sittingId = sittings?.items?.[0]?.id;
    if (sittingId) {
      const detail = await step("sitting detail", `/api/v1/orgs/${slug}/sittings/${sittingId}`, {
        // Circuits come back on the detail and not on the list; the sittings
        // screen relied on the list carrying them until this caught it.
        expect: (p) => must(Array.isArray(p.circuits), "no circuits on the detail"),
      });
      await step("sitting report", `/api/v1/orgs/${slug}/sittings/${sittingId}/report`);
      const circuitId = detail?.circuits?.[0]?.id;
      if (circuitId) {
        await step("circuit console", `/api/v1/orgs/${slug}/circuits/${circuitId}/console`, {
          expect: (p) => {
            must(p.circuit && p.sitting, "unexpected shape");
            must(Array.isArray(p.slots), "no slots");
          },
        });
      }
    }
  }

  report();
}

function report() {
  const failed = results.filter((r) => !r.ok);
  for (const result of results) {
    console.log(`${result.ok ? "  ok  " : " FAIL "} ${result.label}${result.detail ? ` — ${result.detail}` : ""}`);
  }
  console.log(`\n${results.length - failed.length}/${results.length} passed`);
  process.exit(failed.length === 0 ? 0 : 1);
}

main();
