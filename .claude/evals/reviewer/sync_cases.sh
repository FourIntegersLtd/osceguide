#!/usr/bin/env bash
# Grow cases.jsonl from history: every commit whose message says "caused by <sha>"
# and that changed source files becomes a bug case, unless a case already has its
# fix_sha. Haiku writes the id and the bug sentence from the fix's message and diff.
# Usage: sync_cases.sh            add the missing cases, print their ids
#        sync_cases.sh --score    then run run.sh on them (label new-<date>)
#        sync_cases.sh --pending  only print how many fixes lack a case (no model call)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$(git -C "$HERE" rev-parse --show-toplevel)"
CASES="$HERE/cases.jsonl"
. "$HERE/lib.sh"

have=$(jq -r '.fix_sha[0:8]' "$CASES")
# fix_sha cause_sha files... for each "caused by" fix with no case yet.
pending() {
  git log --no-merges -i --grep='caused by [0-9a-f]\{7,\}' --format='%H' | while read -r fix; do
    grep -qx "${fix:0:8}" <<< "$have" && continue
    cause=$(git log -1 --format=%B "$fix" | grep -oiE 'caused by [0-9a-f]{7,40}' | head -1 | awk '{print $3}')
    git cat-file -e "$cause^{commit}" 2>/dev/null || continue
    files=$(git diff --name-only "$fix^" "$fix" | grep -E "$SRC" | grep -vE "$TESTS" \
      | while read -r f; do git cat-file -e "$cause:$f" 2>/dev/null && echo "$f"; done || true)
    if [ -n "$files" ]; then echo "${fix:0:8} $(git rev-parse --short=8 "$cause") $(echo $files)"; fi
  done
}

if [ "${1:-}" = "--pending" ]; then pending | wc -l | tr -d ' '; exit 0; fi

find_claude
ASK="Below is a commit that fixed a bug. Describe the bug as it exists in the code BEFORE this fix, so a reviewer of the commit that introduced it could be judged on whether they spotted it: one sentence naming the function or component and the wrong behaviour. Also give a short kebab-case id (3-6 words). Reply with JSON only: {\"id\": \"...\", \"bug\": \"...\"}"
NEW=()
while read -r fix cause files; do
  V=$(printf '%s\n\n--- FIX ---\n%s\n' "$ASK" "$(git show --stat --patch "$fix" -- $files | head -c 12000)" \
      | "$CLAUDE" -p --model haiku --setting-sources user --tools "" 2>/dev/null \
      | tr '\n' ' ' | grep -oE '\{.*\}' | head -1 || true)
  # Both fields or nothing: run.sh scores against the bug sentence.
  jq -e '.id and .bug' <<< "${V:-null}" >/dev/null 2>&1 || { echo "$fix: no case written (judge gave no id and bug)" >&2; continue; }
  id=$(jq -r .id <<< "$V")
  base=$id; n=2
  while jq -e --arg id "$id" 'select(.id==$id)' "$CASES" >/dev/null; do id="$base-$n"; n=$((n+1)); done
  jq -nc --arg id "$id" --arg sha "$cause" --arg fix "$fix" --arg files "$files" --argjson v "$V" \
    '{id: $id, kind: "bug", sha: $sha, fix_sha: $fix, files: ($files|split(" ")), bug: $v.bug}' >> "$CASES"
  echo "added $id ($cause, fixed by $fix)"
  NEW+=("$id")
done < <(pending)

[ ${#NEW[@]} -eq 0 ] && { echo "no new cases"; exit 0; }
echo "Read each new line in cases.jsonl before committing: a wrong bug sentence makes a wrong score."
[ "${1:-}" = "--score" ] && "$HERE/run.sh" "new-$(date +%F)" "${NEW[@]}"
exit 0
