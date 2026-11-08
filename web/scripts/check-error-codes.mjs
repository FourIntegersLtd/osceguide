// Does every error code the API can send have a place in the web that knows about it?
//
// ErrorResponse.code is a closed enum in openapi.json. A code the web never mentions reaches a
// person as the server's raw sentence at best and as "Something went wrong" at worst, and nobody
// notices because the happy path never raises it. So each code must be one of:
//   - named in a handler: `hasCode(err, "code", ...)`, a `case "code":`, `code === "code"`, or a key in
//     a `Record<PlatformErrorCode, ...>` copy map (errorCopy.ts, mapAuthApiError.ts ...); or
//   - in KNOWN_GAPS (a code that needs its own copy and has none: fix and delete the entry), or
//   - in GENERIC below, with the reason the generic message (the server's own sentence, shown by
//     `errorMessage`) is the right behaviour for it.
//
// Allow-lists only shrink: each list carries its own ceiling.
//
// Usage: node scripts/check-error-codes.mjs

import { allowList, finish, read, sourceFiles, spec } from "./lib-src.mjs";

// Listed code by code, never by pattern, so a new code is not exempt until somebody reads it.

const GENERIC_GROUPS = [
  [
    "a missing or gone record: the 404 sentence ('X not found') is the whole story and screens show it through errorMessage",
    [
      "account_not_found", "announcement_not_found", "assistant_session_not_found",
      "attempt_not_found", "billing_event_not_found", "cv_not_found", "debrief_not_found",
      "entitlement_not_found", "generation_profile_not_found", "gone", "inbox_message_not_found",
      "invoice_not_found", "job_not_found", "media_not_found", "membership_not_found",
      "message_not_found", "not_found", "org_not_found", "payment_not_found",
      "peer_session_not_found", "plan_not_found", "post_not_found", "practice_session_not_found",
      "receipt_not_found", "reporter_not_found", "scim_not_found", "scim_token_not_found",
      "set_entry_not_found", "station_flag_not_found", "station_import_not_found",
      "station_template_not_found", "station_template_version_not_found", "tutor_note_not_found",
      "version_not_found",
    ],
  ],
  [
    "SCIM errors go to the identity provider's client, never to a screen",
    [
      "scim_invalid_filter", "scim_invalid_value", "scim_mutability", "scim_unauthorized",
      "scim_uniqueness",
    ],
  ],
  [
    "input rejected: the server's sentence names the field or file and the fix",
    [
      "content_too_long", "contract_end_in_past", "draft_exists", "empty_content",
      "empty_plan_update", "empty_query",
      "invalid_attempt_state", "invalid_audience", "invalid_author_filter",
      "invalid_avatar_file", "invalid_bucket", "invalid_cv_file", "invalid_date_range",
      "invalid_email_change_token", "invalid_exam_code", "invalid_exam_settings",
      "invalid_invoice_line", "invalid_legacy_token", "invalid_media_status", "invalid_message",
      "invalid_photo", "invalid_refresh_token", "invalid_saml_connection", "invalid_signature",
      "invalid_sso_binding", "invalid_trial_transcript", "invalid_webhook",
      "payout_account_number_required", "platform_admin_exists",
      "practice_access_exists", "referral_code_taken", "request_too_large", "slug_taken", "sso_binding_taken",
      "tag_too_long", "too_many_tags", "tool_arguments_invalid", "unknown_assistant_type",
      "unknown_media_kind", "unknown_partner", "unknown_plan", "unknown_sso_provider",
      "unknown_tool", "unusable_title",
    ],
  ],
  [
    "a state refusal: the server's sentence says what state the thing is in and what to do (shown by errorMessage)",
    [
      "already_published", "assistant_session_not_joinable", "assistant_session_not_ready",
      "assistant_session_not_yours", "attempt_mismatch", "attempt_not_joinable",
      "attempt_not_ready", "audience_not_yours", "av_already_running", "av_not_running",
      "av_unavailable", "cannot_claim_own_post",
      "cannot_revoke_own_console_access", "claim_outside_item",
      "conflict", "exam_not_in_pilot",
      "exam_not_publishable", "fact_check_running", "generation_empty", "generation_unavailable",
      "import_not_ready", "invitation_pending", "job_not_cancellable",
      "job_not_retryable", "knowledge_unavailable", 
      "legacy_exchange_unavailable", "marker_unavailable", "marking_not_ready",
      "media_already_published", "media_being_produced", "media_not_deletable",
      "media_not_editable", "media_not_published", "media_wrong_kind", "message_not_retryable",
      "mfa_already_enrolled", "mfa_not_enrolled", "not_a_media_block", 
      "not_a_partner_reporter", "not_a_stripe_payment", "not_deletable",
      "not_editable", "not_your_post", "password_already_chosen",
      "password_reset_not_sent", "payment_already_recorded", "payment_already_refunded",
      "payment_not_yet_recorded", "peer_session_not_open", "photo_not_on_station",
      "photo_storage_unavailable", "post_not_yours", "post_unavailable",
      "practice_feedback_not_open", "practice_session_not_accepted", "price_creation_failed",
      "programme_not_active", "referral_not_redeemed", "script_not_checked",
      "set_entry_has_attempts", "set_has_attempts", "sso_login_unavailable",
      "sso_not_configurable", "sso_provider_unsupported", "sso_verification_failed",
      "station_being_produced", "station_empty", "station_has_no_template",
      "station_version_not_usable", "stripe_refund_refused", "template_not_published",
      "too_many_streams", "unauthenticated", "unavailable",
    ],
  ],
];

const KNOWN_GAPS = allowList(
  {
    account_suspended: "a suspended person should be told who to contact, not shown a raw sentence",
    password_change_required: "sign-in should route to the change-password step",
    checkout_failed: "should say no money has left the account, as the other checkout errors do",
    stripe_refund_failed: "staff should be told the refund did not happen and can be retried",
  },
  4, // lower only
);

const GENERIC = allowList(
  Object.fromEntries(GENERIC_GROUPS.flatMap(([reason, list]) => list.map((c) => [c, reason]))),
  165, // lower only
);

const codes = spec().components.schemas.ErrorResponse.properties.code.enum;

// What counts as handling a code: it is an argument of hasCode(...), a `case` label, compared with
// `code ===`, or a key of a Record<PlatformErrorCode, ...> copy map. A bare mention does not count.
const handled = new Set();
// Files that map codes by their own shape (a field map, a retry list, a synthesised code).
const COPY_FILES = [
  "domains/assess/errorCopy.ts",
  "domains/assess/trainee/support.ts",
  "capabilities/account/settings/checkoutErrors.ts",
  "capabilities/account/settings/ChangePassword.tsx",
  "capabilities/account/support/mapAuthApiError.ts",
  "capabilities/peer-practice/support/failure.ts",
  "foundation/platform-client/client.ts",
];
const quoted = (text) => [...text.matchAll(/["'`]([a-z][a-z0-9_]*)["'`]/g)].map((m) => m[1]);
for (const f of sourceFiles()) {
  const s = read(f);
  if (!/PlatformErrorCode|hasCode|\bcode\b/.test(s)) continue;
  if (COPY_FILES.some((c) => f.endsWith(c))) {
    const code = s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
    quoted(code).forEach((c) => handled.add(c));
    for (const k of code.matchAll(/^\s*([a-z][a-z0-9_]*)\s*:/gm)) handled.add(k[1]);
  }
  for (const m of s.matchAll(/hasCode\(([^)]*)\)/g)) quoted(m[1]).forEach((c) => handled.add(c));
  for (const m of s.matchAll(/\bcase ["'`]([a-z][a-z0-9_]*)["'`]\s*:/g)) handled.add(m[1]);
  for (const m of s.matchAll(/\bcode\b[^=\n]{0,20}[!=]==\s*["'`]([a-z][a-z0-9_]*)["'`]/g)) handled.add(m[1]);
  for (const m of s.matchAll(/Record<PlatformErrorCode[^=]*=\s*\{([\s\S]*?)\n\};/g))
    for (const k of m[1].matchAll(/^\s*["']?([a-z][a-z0-9_]*)["']?\s*:/gm)) handled.add(k[1]);
}

const offenders = codes.filter((c) => !handled.has(c) && !KNOWN_GAPS.has(c) && !GENERIC.has(c));
finish("check-error-codes", offenders.map((c) => `unhandled code: ${c}`), KNOWN_GAPS, GENERIC);
