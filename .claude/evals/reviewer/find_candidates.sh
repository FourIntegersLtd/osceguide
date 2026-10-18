#!/usr/bin/env bash
# Candidate bug cases for the reviewer eval: for each fix commit, blame the
# source lines it changed (at fix^) to find the commit that wrote them.
# Prints one line per fix: fix_sha | top suspect shas (lines blamed) | files | subject.
# A human (or an Explore agent) confirms each pair before it goes in cases.jsonl.
# Usage: find_candidates.sh [since-date]   (default 2026-08-01)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$(git rev-parse --show-toplevel)"
SINCE=${1:-2026-08-01}
. "$HERE/lib.sh"

git log --since="$SINCE" --no-merges --format='%h%x09%s' \
  | grep -iE $'\t''.*(no longer|\bfix(es|ed)?\b|^stop |caused by|regress)' \
  | while IFS=$'\t' read -r fix subject; do
  files=$(git diff --name-only "$fix^" "$fix" | grep -E "$SRC" | grep -vE "$TESTS" || true)
  [ -z "$files" ] && continue
  blamed=$(for f in $files; do
    git cat-file -e "$fix^:$f" 2>/dev/null || continue
    # Old-side hunks of lines the fix removed or changed: @@ -start,count
    git diff -U0 "$fix^" "$fix" -- "$f" | sed -nE 's/^@@ -([0-9]+)(,([0-9]+))? .*/\1 \3/p' \
      | while read -r start count; do
          count=${count:-1}; [ "$count" = 0 ] && continue
          git blame -s -l -L "$start,+$count" "$fix^" -- "$f" 2>/dev/null | cut -c1-9
        done
  done | sort | uniq -c | sort -rn | head -3 | awk '{printf "%s(%s) ", $2, $1}')
  [ -z "$blamed" ] && continue
  printf '%s | %s| %s | %s\n' "$fix" "$blamed" "$(echo $files | tr '\n' ' ')" "$subject"
done
