# Shared by run.sh, find_candidates.sh and sync_cases.sh. Source it, don't run it.
# Source and test file rules, as in .claude/hooks/quality-gate.sh (CODE, test-file grep).
SRC='\.(py|ts|tsx|js|mjs|sql|sh)$'
TESTS='(^|/)(tests?|e2e)/|\.test\.tsx?$|\.spec\.ts$|_test\.py$|(^|/)test_[^/]*\.py$'

# Sets CLAUDE to the claude CLI (CLAUDE_BIN overrides), or exits.
find_claude() {
  CLAUDE=${CLAUDE_BIN:-$(command -v claude || ls -d "$HOME"/.cursor/extensions/anthropic.claude-code-*/resources/native-binary/claude "$HOME"/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | tail -1)}
  [ -x "$CLAUDE" ] || { echo "claude CLI not found; set CLAUDE_BIN" >&2; exit 1; }
}
