#!/bin/bash
# Run the legacy sync yourself, any time (for example before the 03:00 job).
#
#   scripts/sync_b2c_now.sh                 # production: shows what is pending, asks, then copies
#   scripts/sync_b2c_now.sh staging         # same against staging
#   scripts/sync_b2c_now.sh production --yes   # no question asked
#
# Step 1 is always a preview that writes nothing. Step 2 copies only what the preview listed.
# Full guide: api/docs/LEGACY-SYNC.md
set -u
environment="production"
assume_yes="no"
for argument in "$@"; do
  case "$argument" in
    production|staging) environment="$argument" ;;
    --yes) assume_yes="yes" ;;
    *) echo "usage: $0 [production|staging] [--yes]" >&2; exit 2 ;;
  esac
done
here="$(cd "$(dirname "$0")" && pwd)"

echo "---- Preview for $environment (nothing is written) ----"
"$here/sync_b2c_nightly.sh" "$environment" --dry-run
if [ "$assume_yes" != "yes" ]; then
  printf "Copy these now to %s? [y/N] " "$environment"
  read -r answer
  [ "$answer" = "y" ] || [ "$answer" = "Y" ] || { echo "Stopped. Nothing was copied."; exit 0; }
fi
echo "---- Copying to $environment ----"
"$here/sync_b2c_nightly.sh" "$environment"
