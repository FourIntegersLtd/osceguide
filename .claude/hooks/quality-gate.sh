#!/usr/bin/env bash
# quality-gate: asks for a quality-reviewer pass once per code change.
# Only files THIS session edited count: PostToolUse (Edit/Write/MultiEdit/
# NotebookEdit, subagents included) appends each path to a per-session log, and
# Stop reviews the uncommitted code files on that log. Other sessions' edits in
# the same tree are ignored. Files changed only through Bash are not seen.
# Stop blocks once when those files' diff has changed since the last stop,
# asking the main agent to run quality-reviewer; the stop that follows the
# review (stop_hook_active) records the new diff and lets the turn end, so fixes
# made from the review are not reviewed again.
# QUALITY_GATE_OFF=1 turns it off.
# The CODE globs below are also the agent's file list (quality-reviewer.md).
[ -n "$QUALITY_GATE_OFF" ] && exit 0
IN=$(cat)
EVENT=$(printf '%s' "$IN" | jq -r '.hook_event_name // ""' 2>/dev/null)
SID=$(printf '%s' "$IN" | jq -r '.session_id // "nosession"' 2>/dev/null)
ACTIVE=$(printf '%s' "$IN" | jq -r '.stop_hook_active // false' 2>/dev/null)
ROOT="${CLAUDE_PROJECT_DIR:-.}"
cd "$ROOT" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
ROOT=$(git rev-parse --show-toplevel)

DIR="${TMPDIR:-/tmp}/claude-quality-gate"
mkdir -p "$DIR" 2>/dev/null
STATE="$DIR/$SID"
EDITED="$DIR/$SID.files"

if [ "$EVENT" = "PostToolUse" ]; then
  P=$(printf '%s' "$IN" | jq -r '.tool_input.file_path // .tool_input.notebook_path // ""' 2>/dev/null)
  [ -z "$P" ] && exit 0
  # Physical path, so a symlinked checkout (/var vs /private/var) still matches.
  D=$(cd "$(dirname "$P")" 2>/dev/null && pwd -P) && P="$D/$(basename "$P")"
  echo "${P#"$ROOT"/}" >> "$EDITED"
  exit 0
fi

if [ "$EVENT" = "SessionStart" ]; then
  : > "$EDITED"
  : > "$STATE"
  exit 0
fi

CODE=(':(glob)**/*.py' ':(glob)**/*.ts' ':(glob)**/*.tsx' ':(glob)**/*.js'
      ':(glob)**/*.mjs' ':(glob)**/*.css' ':(glob)**/*.sql' ':(glob)**/*.sh'
      ':(exclude,glob)**/schema.d.ts' ':(exclude,glob)**/_generated/**'
      ':(exclude,glob)**/node_modules/**')
DIRTY=$({ git diff --name-only HEAD -- "${CODE[@]}"
          git ls-files --others --exclude-standard -- "${CODE[@]}"; } 2>/dev/null | sort -u)
MINE=$(sort -u "$EDITED" 2>/dev/null)
FILES=$(comm -12 <(printf '%s\n' "$DIRTY") <(printf '%s\n' "$MINE") | sed '/^$/d')
HASH=$(printf '%s\n' "$FILES" | while read -r f; do [ -n "$f" ] && { echo "$f"; git diff HEAD -- "$f" 2>/dev/null || true; [ -f "$f" ] && cat "$f"; }; done | shasum | cut -c1-40)

LAST=$(cat "$STATE" 2>/dev/null)
# Record before the early exits: the stop after a review must save the post-fix diff.
echo "$HASH" > "$STATE"
[ -z "$FILES" ] && exit 0
[ "$ACTIVE" = "true" ] && exit 0
[ "$HASH" = "$LAST" ] && exit 0

LIST=$(printf '%s' "$FILES" | head -40 | tr '\n' ' ')
# Warn-only: app code changed but no test file did.
NOTE=""
printf '%s\n' "$FILES" | grep -qE '(^|/)(tests?/|e2e/)|(\.test\.tsx?|\.spec\.ts|_test\.py)$|(^|/)test_[^/]*\.py$' \
  || NOTE=" No test file changed with this code: add a failing-first test, or say why none is needed."
jq -n --arg files "$LIST" --arg note "$NOTE" '{
  decision: "block",
  reason: ("Code this session edited changed since the last quality review. Before finishing, run the quality-reviewer agent (Agent, subagent_type quality-reviewer, model sonnet) on these uncommitted files: " + $files + ". Fix every Must fix finding (or say why it does not apply), mention any Worth doing ones you left, then finish." + $note)
}'
