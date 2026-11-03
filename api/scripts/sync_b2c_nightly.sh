#!/bin/bash
# Nightly: copy what is new or changed on the old consumer site into the platform database.
#
#   scripts/sync_b2c_nightly.sh production            # copy for real
#   scripts/sync_b2c_nightly.sh staging --dry-run     # preview only
#   scripts/sync_b2c_nightly.sh production --baseline-before 2026-10-20T00:00:00+00:00   # first run only
#
# Runs scripts/sync_b2c.py under Railway's own Postgres service, so the database secret is never
# printed or copied. Everything is appended to ~/Library/Logs/osce-legacy-sync.log.
# Needs: `railway login` done once on this Mac and this folder linked to the project.
set -u
environment="${1:-}"
shift || true
case "$environment" in
  production) service="platform-postgres-production" ;;
  staging) service="platform-postgres" ;;
  *) echo "usage: $0 production|staging [--dry-run] [--baseline-before ISO_TIME]" >&2; exit 2 ;;
esac

export PATH="/opt/homebrew/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
# The Firebase key lives beside the workspace; override by exporting the variable first.
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/Documents/Projects/OSCE Guide/serviceAccountKey.json}"
cd "$(dirname "$0")/.." || exit 1

mode="--no-dry-run"
extra=()
for argument in "$@"; do
  if [ "$argument" = "--dry-run" ]; then mode="--dry-run"; else extra+=("$argument"); fi
done

log="$HOME/Library/Logs/osce-legacy-sync.log"
{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') sync $environment $mode"
  # Files first: copy whatever the old site added to its bucket into the platform bucket, so every
  # link the sync writes below already resolves. Skipped on a dry run.
  if [ "$mode" = "--no-dry-run" ]; then
    railway run -s "$service" -e "$environment" \
      poetry run python scripts/copy_to_platform_bucket.py --live 2>&1 | grep -v "FutureWarning\|warnings.warn"
  fi
  railway run -s "$service" -e "$environment" \
    poetry run python scripts/sync_b2c.py --database-url-env RAILWAY_PROXY "$mode" ${extra[@]+"${extra[@]}"} 2>&1 \
    | grep -v "FutureWarning\|warnings.warn"
  echo "=== exit ${PIPESTATUS[0]}"
} >> "$log" 2>&1
tail -n 40 "$log"
