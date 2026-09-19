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

/*
 * `allow` lists statuses that are an answer rather than a failure — a 403 from
 * the platform scope means this account is not a platform admin, which is a
 * fact about the seed and not a broken route.
 */
async function step(label, path, { method = "GET", body, expect, allow = [] } = {}) {
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
    if (allow.includes(response.status)) {
      results.push({ label, ok: true, detail: `${response.status} ${payload?.code ?? ""}`.trim() });
      return null;
    }
    if (!response.ok) throw new Error(`${response.status} ${payload?.code ?? ""}`);
    if (expect) expect(payload);
    results.push({ label, ok: true });
    return payload;
  } catch (error) {
    results.push({ label, ok: false, detail: error.message });
    return null;
  }
}

/** The five listings the authoring capability renders under either prefix. */
const AUTHORING_LISTINGS = [
  ["stations", "stations"],
  ["station templates", "station-templates"],
  ["feedback templates", "feedback-templates"],
  ["rubrics", "rubrics"],
  ["exams", "exams"],
];

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

  await step("my station sets", "/api/v1/me/station-sets", {
    // The list carries each set's entries, which is what lets the mocks
    // screens work out attempted, incomplete and combinable stations without
    // a request per set. If that stops being true, three screens go quiet.
    expect: (p) => must(Array.isArray(p.items), "not a page"),
  });

  // Build a session the way the Setup tab does, then run its whole loop:
  // start an attempt at the first entry, and ask to debrief it.
  const forSet = await step("library for a session", "/api/v1/stations?limit=2");
  if (forSet?.items?.length) {
    const set = await step("create a session", "/api/v1/me/station-sets", {
      method: "POST",
      body: {
        name: `Smoke session ${Date.now()}`,
        exam_code: forSet.items[0].exam_code,
        station_version_ids: forSet.items.map((station) => station.version_id),
      },
      expect: (p) => must(Array.isArray(p.entries) && p.entries.length > 0, "no entries"),
    });
    if (set) {
      await step("read the session back", `/api/v1/me/station-sets/${set.id}`, {
        expect: (p) => must(p.total_entries === set.total_entries, "entry count moved"),
      });
      const entryId = set.entries[0].id;
      const started = await step(
        "start a station in it",
        `/api/v1/me/station-sets/${set.id}/entries/${entryId}/attempts`,
        { method: "POST", expect: (p) => must(p.attempt_id, "no attempt id") },
      );
      if (started) {
        await step("debrief it", `/api/v1/me/station-sets/${set.id}/entries/${entryId}/debriefs`, {
          method: "POST",
          expect: (p) => must(p.attempt_id, "no debrief attempt id"),
        });
        await step("abandon the session attempt", `/api/v1/attempts/${started.attempt_id}/abandon`, {
          method: "POST",
        });
      }
    }
  }
  /*
   * The trainee arm. One feed drives the overview and the sitting page, so the
   * shape of a slot inside it is what those screens depend on — `joinable` and
   * `exam_completed_at` decide whether somebody is offered a way into a
   * station, and `attempt_id` is the only route to their own record.
   */
  const mySittings = await step("my sittings", "/api/v1/me/sittings", {
    expect: (p) => {
      must(Array.isArray(p.items), "not a list");
      for (const sitting of p.items) {
        must(typeof sitting.can_join === "boolean", "no can_join on a sitting");
        must(typeof sitting.circuit_id === "string", "no circuit on a sitting");
        for (const slot of sitting.slots ?? []) {
          must(typeof slot.slot_index === "number", "no slot_index");
          must("exam_completed_at" in slot, "no exam_completed_at");
          must("attempt_id" in slot, "no attempt_id on a slot");
        }
      }
    },
  });
  const myFirstSitting = mySittings?.items?.[0];
  if (myFirstSitting) {
    /*
     * A result nobody has released is a 404 here, not an empty document — the
     * sitting page treats that as "no link yet" rather than a failure.
     */
    await step("my result", `/api/v1/me/results/${myFirstSitting.id}`, { allow: [403, 404] });
    if (myFirstSitting.can_join) {
      await step(
        "join my circuit",
        `/api/v1/me/circuits/${myFirstSitting.circuit_id}/join-token`,
        { expect: (p) => must(typeof p.token === "string", "no room token") },
      );
    }
  }
  await step("discussion", "/api/v1/community/questions?limit=5", {
    expect: (p) => must(Array.isArray(p.items), "not a page"),
  });
  await step("stream ticket", "/api/v1/auth/stream-ticket", {
    method: "POST",
    expect: (p) => must(typeof p.ticket === "string", "no ticket"),
  });
  // The account capability: the person, what they may practise, what they paid,
  // who they referred and what the tutor remembers.
  await step("plans", "/api/v1/billing/plans", {
    expect: (p) => must(Array.isArray(p.items), "not a page"),
  });
  await step("my entitlements", "/api/v1/me/entitlements", {
    expect: (p) => {
      must(Array.isArray(p.items), "not a page");
      // A gate reads `live` and nothing else; the list carries revoked and
      // expired rows too.
      for (const item of p.items) must(typeof item.live === "boolean", "no live flag");
    },
  });
  /*
   * Receipts are ids, not documents. The settings screen was written against
   * the detail shape until this said otherwise — `domains/train/Access.tsx`
   * still reads `plan_label` off this list and renders nothing.
   */
  const receipts = await step("my receipts", "/api/v1/me/receipts", {
    expect: (p) => {
      must(Array.isArray(p.items), "not a page");
      for (const item of p.items) must(typeof item === "string", "receipts are ids, not objects");
    },
  });
  const receiptId = receipts?.items?.[0];
  if (receiptId) {
    await step("one receipt", `/api/v1/me/receipts/${receiptId}`, {
      expect: (p) => must(typeof p.plan_label === "string", "no plan label"),
    });
  }
  await step("my referrals", "/api/v1/me/referrals", {
    expect: (p) => must(typeof p.code === "string" && typeof p.earned_pence === "number", "unexpected shape"),
  });
  await step("what the tutor remembers", "/api/v1/me/tutor-memory", {
    expect: (p) => must(Array.isArray(p.notes) && Array.isArray(p.events), "unexpected shape"),
  });

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

    /*
     * Authoring reads both scopes, because that is the claim the capability
     * makes: the same five listings under `/orgs/{slug}` and under
     * `/platform`. If one prefix drifts, one implementation can no longer
     * serve both arms, and this is where that is caught rather than in a
     * browser on whichever arm somebody happened to open.
     */
    for (const [label, path] of AUTHORING_LISTINGS) {
      await step(`org ${label}`, `/api/v1/orgs/${slug}/${path}`, {
        expect: (p) => must(Array.isArray(p.items), "not a page"),
      });
    }
    /*
     * Self practice reads the same list the authoring screens write, because a
     * trainee is an `OrgReader` and the org's library is one library. What the
     * screen needs off a row is the published version it would sit: without
     * `current_version_id` the station is a button that can only ever fail.
     */
    await step("org stations for self practice", `/api/v1/orgs/${slug}/stations`, {
      expect: (p) => {
        must(Array.isArray(p.items), "not a page");
        for (const station of p.items) {
          must(typeof station.status === "string", "no station status");
          must("current_version_id" in station, "no current_version_id");
        }
      },
    });
    await step("org programmes", `/api/v1/orgs/${slug}/programmes`, {
      expect: (p) => must(Array.isArray(p.items), "not a page"),
    });

    for (const [label, path] of AUTHORING_LISTINGS) {
      // Exams are the one listing that is not the scope plus a name:
      // `/platform/exams` is POST-only and the catalogue is unscoped.
      const listing = path === "exams" ? "/api/v1/exams" : `/api/v1/platform/${path}`;
      await step(`platform ${label}`, listing, {
        allow: [403],
        expect: (p) => must(Array.isArray(p.items), "not a page"),
      });
    }
    /*
     * The staff console's own reads.
     *
     * Reads only. There is no delete for an organisation — deliberately, since
     * a tenant's rows include results that have to stay defensible — so a
     * smoke run must not provision one it cannot take back.
     *
     * The last two steps allow either answer, and that is the honest shape of
     * them: this account is a platform admin *and* an admin of the org it
     * switched into, so it reads both through its membership. Against an
     * organisation it does not belong to, both answer 403 — `OrgAdmin` is
     * declared `allow_platform_admin=False`, so a console admin may read an
     * organisation for support and inherits none of its powers. That is why
     * the staff console shows neither. `docs/port-gaps.md` carries it.
     */
    await step("platform overview", "/api/v1/platform/overview", {
      allow: [403],
      expect: (p) => {
        must(typeof p.organizations === "number", "no organisation count");
        must(typeof p.users === "number", "no user count");
      },
    });
    await step("platform organizations", "/api/v1/platform/organizations?limit=5", {
      allow: [403],
      expect: (p) => {
        must(Array.isArray(p.items), "not a page");
        for (const org of p.items) {
          must(typeof org.slug === "string", "no slug to address it by");
          must(typeof org.status === "string", "no status to colour it by");
        }
      },
    });
    await step("platform users", "/api/v1/platform/users?q=dev&limit=5", {
      allow: [403],
      expect: (p) => must(Array.isArray(p.items), "not a page"),
    });
    await step("staff reads one organisation", `/api/v1/orgs/${slug}`, {
      expect: (p) => must(typeof p.slug === "string", "not an organisation"),
    });
    await step("org memberships are not the console's", `/api/v1/orgs/${slug}/memberships`, {
      allow: [200, 403],
    });
    await step("org audit is not the console's", `/api/v1/orgs/${slug}/audit`, {
      allow: [200, 403],
    });
    // The exam-day board and the supervisor's own circuits: both were unwired
    // until the dashboard screens were ported, so both are worth watching.
    await step("org live board", `/api/v1/orgs/${slug}/live`, {
      expect: (p) => {
        must(Array.isArray(p.circuits), "not a board");
        must(typeof p.as_of === "string", "no as_of to count down from");
      },
    });
    await step("supervisor circuits", `/api/v1/orgs/${slug}/supervisor/circuits`, {
      expect: (p) => must(Array.isArray(p.items), "not a list"),
    });
    const sittings = await step("org sittings", `/api/v1/orgs/${slug}/sittings`);
    const sittingId = sittings?.items?.[0]?.id;
    if (sittingId) {
      const detail = await step("sitting detail", `/api/v1/orgs/${slug}/sittings/${sittingId}`, {
        // Circuits come back on the detail and not on the list; the sittings
        // screen relied on the list carrying them until this caught it.
        expect: (p) => must(Array.isArray(p.circuits), "no circuits on the detail"),
      });
      const report = await step("sitting report", `/api/v1/orgs/${slug}/sittings/${sittingId}/report`, {
        expect: (p) => {
          must(p.totals && Array.isArray(p.candidates), "unexpected shape");
          // The evidence a release is checked against is built from these.
          for (const candidate of p.candidates) {
            must(Array.isArray(candidate.stations), "a candidate with no stations array");
          }
        },
      });
      // Ranked review order. A training sitting answers 422, which the screen
      // reads as "no ranking here" — so both outcomes are an answer.
      await step("sitting cohort", `/api/v1/orgs/${slug}/sittings/${sittingId}/cohort`, {
        allow: [422],
        expect: (p) => must(Array.isArray(p.candidates), "not a cohort"),
      });
      const slotId = report?.candidates?.[0]?.stations?.[0]?.slot_id;
      if (slotId) {
        await step("slot reviews", `/api/v1/orgs/${slug}/slots/${slotId}/reviews`, {
          // A reviewer's own review is found in here by `submitted_by`: there
          // is no GET for `reviews/mine`, only a PUT.
          expect: (p) => must(Array.isArray(p.items) && p.summary, "unexpected shape"),
        });
        await step("gp lead review", `/api/v1/orgs/${slug}/slots/${slotId}/gp-lead-review`, {
          // 404 is "nobody has written one", which is the usual case.
          allow: [404],
          expect: (p) => must(typeof p.revision === "number", "no revision to save against"),
        });
      }
      const circuitId = detail?.circuits?.[0]?.id;
      if (circuitId) {
        await step("circuit console", `/api/v1/orgs/${slug}/circuits/${circuitId}/console`, {
          expect: (p) => {
            must(p.circuit && p.sitting, "unexpected shape");
            must(Array.isArray(p.slots), "no slots");
            // The runner draws its stepper, its clock and its alerts off
            // these three; a rename would leave the screen blank rather
            // than broken, which is the kind of thing this script is for.
            must("phase" in p.circuit, "no phase on the circuit");
            must("auto_advance" in p.circuit, "no auto_advance on the circuit");
            must(Array.isArray(p.circuit.alerts), "no alerts on the circuit");
          },
        });
        // The record behind every override the runner offers.
        await step(
          "circuit interventions",
          `/api/v1/orgs/${slug}/circuits/${circuitId}/interventions`,
          { expect: (p) => must(Array.isArray(p.items), "not a list") },
        );
        // Subscribe-only by construction: an examiner who could publish
        // could prompt a candidate, so this is a route worth watching.
        await step(
          "observer token",
          `/api/v1/orgs/${slug}/circuits/${circuitId}/observer-token`,
          // 409 is a circuit that is not running, which is the usual seed.
          { method: "POST", allow: [409], expect: (p) => must(p.token && p.server_url, "no grant") },
        );
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
