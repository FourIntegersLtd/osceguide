#!/usr/bin/env bash
# Score the reviewer agent against cases.jsonl.
# Each case: check out its commit in a throwaway worktree (with today's
# .claude/rules laid over it), run today's reviewer.md headless on that commit,
# then a haiku judge decides whether the review named the known bug (bug case)
# or counts its blocking findings (clean case: each one is a false alarm).
# Usage: run.sh <label> [case-id ...]     e.g. run.sh baseline
#        JUDGE_ONLY=1 run.sh <label> ...    re-judge the stored reviews only
# Output: results/<label>/<id>.md (review, gitignored), <id>.json (verdict),
#         summary.json. Needs the claude CLI (CLAUDE_BIN overrides). 3 at a time.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(git -C "$HERE" rev-parse --show-toplevel)
. "$HERE/lib.sh"; find_claude
export CLAUDE HERE ROOT

if [ "${1:-}" = "--one" ]; then
  LABEL=$2; CASE=$(jq -c --arg id "$3" 'select(.id==$id)' "$HERE/cases.jsonl")
  id=$(jq -r .id <<< "$CASE"); sha=$(jq -r .sha <<< "$CASE"); kind=$(jq -r .kind <<< "$CASE")
  OUT="$HERE/results/$LABEL"; WT="${TMPDIR:-/tmp}/reviewer-eval-$LABEL-$id"
  OK=1
  if [ -z "${JUDGE_ONLY:-}" ] || [ ! -s "$OUT/$id.md" ]; then
    rm -rf "$WT"; git -C "$ROOT" worktree prune
    for _ in 1 2 3; do git -C "$ROOT" worktree add -q --detach "$WT" "$sha" 2>/dev/null && break; sleep 2; done
    [ -d "$WT" ] || { echo "$id: worktree failed"; exit 0; }
    mkdir -p "$WT/.claude"; rm -rf "$WT/.claude/rules"; cp -R "$ROOT/.claude/rules" "$WT/.claude/rules"
    PROMPT_FILE="$WT/.reviewer-prompt.md"
    awk 'f>=2; /^---$/{f++}' "$ROOT/.claude/agents/reviewer.md" > "$PROMPT_FILE"
    # Prompt on stdin: the tool-list flags are variadic and would swallow it.
    echo "Review commit $sha, the HEAD of this checkout (start from \`git show HEAD\`), as your instructions describe. Treat it as a change just made; do not look for later history." \
      | (cd "$WT" && "$CLAUDE" -p --model opus --setting-sources user \
          --append-system-prompt-file "$PROMPT_FILE" \
          --allowedTools Read Grep Glob "Bash(git show:*)" "Bash(git diff:*)" "Bash(git log:*)" "Bash(git blame:*)" \
          --disallowedTools Edit Write NotebookEdit Agent) > "$OUT/$id.md" 2>&1 || OK=0
    git -C "$ROOT" worktree remove --force "$WT" 2>/dev/null || rm -rf "$WT"
  fi
  if [ "$OK" = 0 ]; then
    jq -n --arg id "$id" --arg kind "$kind" '{id: $id, kind: $kind, error: "reviewer run failed"}' > "$OUT/$id.json"
    echo "$id: reviewer run failed (see $OUT/$id.md)"; exit 0
  fi
  if [ "$kind" = bug ]; then
    ASK="A code review is below. The change it reviewed contains this known bug: $(jq -r .bug <<< "$CASE") (in $(jq -r '.files|join(", ")' <<< "$CASE")). Did the review report THIS defect (same root problem, not merely the same file)? If several defects are listed, the first one is enough. Reply with JSON only: {\"caught\": true|false, \"why\": \"<one sentence>\"}"
  else
    ASK="A code review is below. List every finding it asks the author to fix. Do not judge whether they are right: include each one presented as a defect or required change, and leave out only those it tags Nit or Pre-existing or calls optional. Reply with JSON only: {\"findings\": [\"<a few words each>\"]}"
  fi
  V=$(printf '%s\n\n--- REVIEW ---\n%s\n' "$ASK" "$(cat "$OUT/$id.md")" \
      | "$CLAUDE" -p --model haiku --setting-sources user --tools "" 2>/dev/null \
      | tr '\n' ' ' | grep -oE '\{.*\}' | head -1 || true)
  jq -n --arg id "$id" --arg kind "$kind" --argjson v "${V:-null}" \
     '{id: $id, kind: $kind} + ($v // {error: "judge gave no JSON"}) | if .findings then .false_alarms = (.findings|length) else . end' > "$OUT/$id.json"
  echo "$id: $(jq -c 'del(.id,.kind)' "$OUT/$id.json")"
  exit 0
fi

LABEL=${1:?usage: run.sh <label> [case-id ...]}; shift
mkdir -p "$HERE/results/$LABEL"
FILTER=$(jq -nc '$ARGS.positional' --args "$@")
# Ids, not whole cases: BSD xargs -I caps a replacement at 255 bytes.
jq -r --argjson only "$FILTER" 'select(($only|length)==0 or (.id|IN($only[]))) | .id' "$HERE/cases.jsonl" \
  | xargs -P 3 -I{} "$0" --one "$LABEL" {} || true

jq -s '{
  bugs: (map(select(.kind=="bug")) | length),
  caught: (map(select(.kind=="bug" and .caught==true)) | length),
  clean: (map(select(.kind=="clean")) | length),
  false_alarms: (map(select(.kind=="clean") | .false_alarms // 0) | add // 0),
  errors: (map(select(.error)) | map(.id)),
  missed: (map(select(.kind=="bug" and .caught!=true)) | map(.id))
}' "$HERE/results/$LABEL"/*.json | tee "$HERE/results/$LABEL/summary.json" \
  | jq -r '"caught \(.caught)/\(.bugs), false alarms \(.false_alarms) on \(.clean) clean" + (if (.errors|length)>0 then ", errors: \(.errors|join(" "))" else "" end)'
