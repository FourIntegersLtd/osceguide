#!/usr/bin/env bash
# quality-gate: asks for a quality-reviewer pass once per code change.
# SessionStart records the code diff the session began with, so changes that
# were already there are not reviewed. Stop blocks once when the code diff has
# changed since the last stop, asking the main agent to run quality-reviewer;
# the stop that follows the review (stop_hook_active) records the new diff and
# lets the turn end, so fixes made from the review are not reviewed again.
# Blocks at most once per code change. QUALITY_GATE_OFF=1 turns it off.
# The CODE globs below are also the agent's file list (quality-reviewer.md).
[ -n "$QUALITY_GATE_OFF" ] && exit 0
IN=$(cat)
EVENT=$(printf '%s' "$IN" | jq -r '.hook_event_name // ""' 2>/dev/null)
SID=$(printf '%s' "$IN" | jq -r '.session_id // "nosession"' 2>/dev/null)
ACTIVE=$(printf '%s' "$IN" | jq -r '.stop_hook_active // false' 2>/dev/null)
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

DIR="${TMPDIR:-/tmp}/claude-quality-gate"
mkdir -p "$DIR" 2>/dev/null
STATE="$DIR/$SID"

CODE=(':(glob)**/*.py' ':(glob)**/*.ts' ':(glob)**/*.tsx' ':(glob)**/*.js'
      ':(glob)**/*.mjs' ':(glob)**/*.css' ':(glob)**/*.sql' ':(glob)**/*.sh'
      ':(exclude,glob)**/schema.d.ts' ':(exclude,glob)**/_generated/**'
      ':(exclude,glob)**/node_modules/**')
FILES=$({ git diff --name-only HEAD -- "${CODE[@]}"
          git ls-files --others --exclude-standard -- "${CODE[@]}"; } 2>/dev/null | sort -u)
HASH=$({ git diff HEAD -- "${CODE[@]}"
         git ls-files --others --exclude-standard -z -- "${CODE[@]}" | xargs -0 cat; } 2>/dev/null \
       | shasum | cut -c1-40)

if [ "$EVENT" = "SessionStart" ]; then
  echo "$HASH" > "$STATE"
  exit 0
fi

LAST=$(cat "$STATE" 2>/dev/null)
# Record before the early exits: the stop after a review must save the post-fix diff.
echo "$HASH" > "$STATE"
[ -z "$FILES" ] && exit 0
[ "$ACTIVE" = "true" ] && exit 0
[ "$HASH" = "$LAST" ] && exit 0

LIST=$(printf '%s' "$FILES" | head -40 | tr '\n' ' ')
jq -n --arg files "$LIST" '{
  decision: "block",
  reason: ("Code changed since the last quality review. Before finishing, run the quality-reviewer agent (Agent, subagent_type quality-reviewer, model sonnet) on these uncommitted files: " + $files + ". Fix every Must fix finding (or say why it does not apply), mention any Worth doing ones you left, then finish.")
}'
