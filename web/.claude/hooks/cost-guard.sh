#!/usr/bin/env bash
# cost-guard: warn-only PreToolUse hook. Never blocks, never fails the tool call.
# Rationale and measurements: ~/.claude/projects/*/memory/long-sessions-burn-usage.md
# Repo copy for cloud sessions. On a machine that already runs the user-level
# copy, step aside so each warning fires once.
[ -x "$HOME/.claude/hooks/cost-guard.sh" ] && exit 0
IN=$(cat)
TOOL=$(printf '%s' "$IN" | jq -r '.tool_name // ""' 2>/dev/null)
SID=$(printf '%s' "$IN" | jq -r '.session_id // "nosession"' 2>/dev/null)
[ -z "$TOOL" ] && exit 0

DIR="${TMPDIR:-/tmp}/claude-cost-guard"
mkdir -p "$DIR" 2>/dev/null
NOW=$(date +%s)
MSG=""
CTX=""

add() { # $1 banner fragment, $2 context sentence
  [ -n "$1" ] && { [ -n "$MSG" ] && MSG="$MSG; "; MSG="$MSG$1"; }
  [ -n "$2" ] && { [ -n "$CTX" ] && CTX="$CTX "; CTX="$CTX$2"; }
}

case "$TOOL" in
Agent)
  F="$DIR/$SID.agents"
  TYPE=$(printf '%s' "$IN" | jq -r '.tool_input.subagent_type // "claude"' 2>/dev/null)
  MODEL=$(printf '%s' "$IN" | jq -r '.tool_input.model // ""' 2>/dev/null)
  echo "$NOW" >> "$F"
  CUT=$((NOW - 600))
  N=$(awk -v c="$CUT" '$1>=c {n++} END {print n+0}' "$F" 2>/dev/null)
  [ -z "$N" ] && N=1

  if [ "$N" -gt 4 ]; then
    add "fan-out $N/4 in 10min" "COST GUARD: you have spawned $N subagents in the last 10 minutes; the measured cap for this machine is 3-4 at a time. On 2026-09-24, 16 concurrent agents burned 41% of a day's usage limit in 18 minutes and finished no sooner than a smaller batch would have. Do not spawn more in parallel right now: let the running agents return first, or fold the remaining work into one agent."
  fi

  case "$TYPE" in
  general-purpose|claude)
    add "$TYPE (Explore is cheaper)" "COST GUARD: this agent is '$TYPE', which boots with the full tool schema plus every skill description -- about 24k tokens before it does any work -- and inherits the parent's premium model. If its job is read-only (audit, parity check, search, 'find where X lives'), use subagent_type 'Explore' instead, which is read-only and reads excerpts rather than whole files."
    ;;
  esac

  if [ -z "$MODEL" ] && [ "$N" -gt 1 ]; then
    add "" "COST GUARD: no 'model' was set on this Agent call, so it inherits the parent's model. For sweeps, greps and audits set model: 'haiku' or 'sonnet' -- paying premium rates for grep work was a measured waste here."
  fi
  ;;
Bash)
  F="$DIR/$SID.bash"
  N=$(cat "$F" 2>/dev/null)
  case "$N" in ''|*[!0-9]*) N=0 ;; esac
  N=$((N + 1))
  echo "$N" > "$F"
  if [ $((N % 75)) -eq 0 ]; then
    add "${N} Bash calls this session" "COST GUARD: this session has made $N Bash calls. Every tool call replays the entire context, so call count -- not command size -- is the main cost multiplier once context is large. Batch related greps and reads into one call, and send long output to a file then read the tail, rather than pulling it all into context."
  fi
  ;;
esac

[ -z "$CTX" ] && exit 0
jq -cn --arg m "cost-guard: ${MSG:-see context}" --arg c "$CTX" \
  '{systemMessage:$m, suppressOutput:true, hookSpecificOutput:{hookEventName:"PreToolUse", additionalContext:$c}}' 2>/dev/null
exit 0
