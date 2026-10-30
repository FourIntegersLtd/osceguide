#!/usr/bin/env bash
# quality-gate: a code change is not finished until its owner proved it and
# quality-reviewer read it.
# Only files THIS session edited count: PostToolUse (Edit/Write/MultiEdit/
# NotebookEdit, subagents included) appends each path to a per-session log.
# Files changed only through Bash are not seen.
# Stop compares those files against the commit the session started from, so a
# change committed inside the turn is still checked. It then looks in the
# transcript, from the prompt that started the change, for:
#   - an Agent call with subagent_type quality-reviewer, and one with
#     subagent_type reviewer (opus: Sonnet owners write, Opus checks), and
#   - for each owner of a changed api/, web/ or assessment/ file
#     (.claude/OWNERS.md), that owner agent or its verify skill.
#   - on a high-risk change (an access-owner file, a money path another owner
#     holds, a migration or a CI workflow): the security-review skill too, and
#     the user is told it needs their review.
# Missing evidence blocks the stop, up to 3 times per change; then the stop is
# let through and the user is told what was skipped. Once the evidence is there
# the current diff is recorded, so fixes made from the review are not reviewed
# again.
# UserPromptSubmit stamps the turn's start and reminds the agent of the route.
# SessionStart resets the log only on a fresh start: compact and resume keep it.
# QUALITY_GATE_OFF=1 turns it off.
# The CODE globs below are also the agent's file list (quality-reviewer.md).
[ -n "$QUALITY_GATE_OFF" ] && exit 0
IN=$(cat)
field() { printf '%s' "$IN" | jq -r "$1" 2>/dev/null; }
EVENT=$(field '.hook_event_name // ""')
SID=$(field '.session_id // "nosession"')
ROOT="${CLAUDE_PROJECT_DIR:-.}"
cd "$ROOT" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
ROOT=$(git rev-parse --show-toplevel)

DIR="${TMPDIR:-/tmp}/claude-quality-gate"
mkdir -p "$DIR" 2>/dev/null
STATE="$DIR/$SID"           # diff hash last reviewed
EDITED="$DIR/$SID.files"    # paths this session edited
BASE_F="$DIR/$SID.base"     # HEAD when the session started
TURN="$DIR/$SID.turn"       # when the latest prompt arrived
SINCE="$DIR/$SID.since"     # start of the turn the unreviewed change began in
BLOCKS="$DIR/$SID.blocks"   # stops blocked for that change
now() { date -u +%Y-%m-%dT%H:%M:%S; }

case "$EVENT" in
  SessionStart)
    if [ "$(field '.source // "startup"')" = "startup" ]; then
      : > "$EDITED"; : > "$STATE"; rm -f "$SINCE" "$BLOCKS" "$TURN"
      git rev-parse HEAD > "$BASE_F" 2>/dev/null
    fi
    [ -s "$BASE_F" ] || git rev-parse HEAD > "$BASE_F" 2>/dev/null
    # Fixes committed with "caused by <sha>" but not yet a reviewer eval case.
    N=$("$ROOT/.claude/evals/reviewer/sync_cases.sh" --pending 2>/dev/null || echo 0)
    [ "${N:-0}" -gt 0 ] && jq -n --arg n "$N" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext:
      ("\($n) committed fix(es) say \"caused by <sha>\" but have no reviewer eval case. Tell the user, and offer to run .claude/evals/reviewer/sync_cases.sh --score.")}}'
    exit 0 ;;
  UserPromptSubmit)
    now > "$TURN"
    jq -n '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext:
      "Code change in api/, web/ or assessment/? Route it through /build-feature or /fix-bug as the owning agent (.claude/OWNERS.md), prove it with that owner'"'"'s verify skill, then run quality-reviewer. Size is no exemption; the Stop hook checks."}}'
    exit 0 ;;
  PostToolUse)
    P=$(field '.tool_input.file_path // .tool_input.notebook_path // ""')
    [ -z "$P" ] && exit 0
    # Physical path, so a symlinked checkout (/var vs /private/var) still matches.
    D=$(cd "$(dirname "$P")" 2>/dev/null && pwd -P) && P="$D/$(basename "$P")"
    echo "${P#"$ROOT"/}" >> "$EDITED"
    [ -s "$SINCE" ] || { cat "$TURN" 2>/dev/null || now; } > "$SINCE"
    exit 0 ;;
esac

# Stop.
BASE=$(cat "$BASE_F" 2>/dev/null)
git cat-file -e "${BASE:-x}^{commit}" 2>/dev/null || BASE=HEAD
CODE=(':(glob)**/*.py' ':(glob)**/*.ts' ':(glob)**/*.tsx' ':(glob)**/*.js'
      ':(glob)**/*.mjs' ':(glob)**/*.css' ':(glob)**/*.sql' ':(glob)**/*.sh'
      ':(glob).github/workflows/*.yml'
      ':(exclude,glob)**/schema.d.ts' ':(exclude,glob)**/_generated/**'
      ':(exclude,glob)**/node_modules/**')
DIRTY=$({ git diff --name-only "$BASE" -- "${CODE[@]}"
          git ls-files --others --exclude-standard -- "${CODE[@]}"; } 2>/dev/null | sort -u)
MINE=$(sort -u "$EDITED" 2>/dev/null)
FILES=$(comm -12 <(printf '%s\n' "$DIRTY") <(printf '%s\n' "$MINE") | sed '/^$/d')
[ -z "$FILES" ] && exit 0
HASH=$(printf '%s\n' "$FILES" | while read -r f; do echo "$f"; git diff "$BASE" -- "$f" 2>/dev/null; [ -f "$f" ] && cat "$f"; done | shasum | cut -c1-40)
settle() { echo "$HASH" > "$STATE"; rm -f "$SINCE" "$BLOCKS"; }
[ "$HASH" = "$(cat "$STATE" 2>/dev/null)" ] && { settle; exit 0; }

# Owners of the changed app files, from the same parser the ownership guard uses.
APP=()
while read -r f; do case "$f" in api/*|web/*|assessment/*) APP+=("$f") ;; esac; done <<< "$FILES"
OWNERS=""; LOOKUP_OK=1
[ ${#APP[@]} -gt 0 ] && { OWNERS=$(python3 - "$ROOT" "${APP[@]}" 2>/dev/null <<'PY'
import importlib.util, sys
root, paths = sys.argv[1], sys.argv[2:]
spec = importlib.util.spec_from_file_location("ownership", f"{root}/api/tests/guards/test_ownership.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
rows = mod.parse_rows(open(f"{root}/.claude/OWNERS.md").read())
print("\n".join(sorted({r.owner for p in paths for r in rows if r.matches(p)})))
PY
) || LOOKUP_OK=0; }
# web-foundation proves with web/'s own `verify` skill, listed as web:verify.
verify_of() { case "$1" in web-foundation-owner) echo "verify" ;; *) echo "verify-${1%-owner}" ;; esac; }

# What ran since the change began (Agent subagent types and Skill names).
FROM=$(cat "$SINCE" 2>/dev/null)
RAN=$(jq -r --arg since "${FROM:-0}" '
  select(.type == "assistant" and (.timestamp // "") >= $since)
  | .message.content[]? | select(.type == "tool_use")
  | if .name == "Agent" or .name == "Task" then "agent:" + (.input.subagent_type // "")
    elif .name == "Skill" then "skill:" + (.input.skill // "")
    else empty end' "$(field '.transcript_path // ""')" 2>/dev/null | sort -u)

MISSING=()
grep -qx 'agent:quality-reviewer' <<< "$RAN" || MISSING+=("quality-reviewer")
grep -qx 'agent:reviewer' <<< "$RAN" || MISSING+=("reviewer (model opus)")
[ "$LOOKUP_OK" = 1 ] || MISSING+=("the owner check (owner lookup from .claude/OWNERS.md failed: run api/tests/guards/test_ownership.py)")
for o in $OWNERS; do
  v=$(verify_of "$o")
  grep -qxE "agent:$o|skill:$v|skill:web:$v" <<< "$RAN" || MISSING+=("$o (or its $v skill)")
done

# High risk is set by the paths, not the author: money and auth, migrations, CI.
# Beyond access-owner's rows: money paths other owners hold (money.md's paths:), alembic, CI.
# A new money folder outside access-owner's rows must be added here.
HIGH=0
grep -qx 'access-owner' <<< "$OWNERS" && HIGH=1
grep -qE '^(api/alembic/|\.github/workflows/|web/src/domains/partner/|web/src/app/staff/(billing|growth|referral-payouts)/)' <<< "$FILES" && HIGH=1
if [ "$HIGH" = 1 ]; then
  grep -qx 'skill:security-review' <<< "$RAN" || MISSING+=("the security-review skill")
fi

[ ${#MISSING[@]} -eq 0 ] && { settle; exit 0; }

LIST=$(printf '%s' "$FILES" | head -40 | tr '\n' ' ')
NEED=$(printf '%s; ' "${MISSING[@]}"); NEED=${NEED%; }
N=$(( $(cat "$BLOCKS" 2>/dev/null || echo 0) + 1 ))
if [ "$N" -gt 3 ]; then
  settle
  jq -n --arg need "$NEED" --arg files "$LIST" \
    '{systemMessage: ("Quality gate gave up after 3 asks. Not run: " + $need + ". Files: " + $files)}'
  exit 0
fi
echo "$N" > "$BLOCKS"
# Warn-only: app code changed but no test file did.
NOTE=""
[ "$HIGH" = 1 ] && NOTE=" High-risk paths (money, auth, migrations or CI): tell the user this change needs their review before commit or promote."
printf '%s\n' "$FILES" | grep -qE '(^|/)(tests?/|e2e/)|(\.test\.tsx?|\.spec\.ts|_test\.py)$|(^|/)test_[^/]*\.py$' \
  || NOTE="$NOTE No test file changed with this code: add a failing-first test, or say why none is needed."
jq -n --arg files "$LIST" --arg need "$NEED" --arg note "$NOTE" '{
  decision: "block",
  reason: ("This session changed code (committed or not): " + $files + ". Not yet run since the change began: " + $need + ". Run each now: the owner agent (Agent, subagent_type <owner>, model sonnet) or its verify skill to prove the change, then the quality-reviewer agent (model sonnet) and the reviewer agent (its own model, opus) on these files, in parallel. Fix every Must fix finding (or say why it does not apply), mention any Worth doing ones you left, and say which owner and skills handled it." + $note)
}'
