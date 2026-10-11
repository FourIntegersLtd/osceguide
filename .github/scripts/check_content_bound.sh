#!/usr/bin/env bash
# Fails when an environment's /health says published stations have no template.
# Usage: check_content_bound.sh <staging|production> [health-json]  (the body may come on stdin)
set -euo pipefail
env_name="${1:?usage: check_content_bound.sh <staging|production> [health-json]}"
body="${2:-$(cat)}"
label="$(echo "${env_name:0:1}" | tr a-z A-Z)${env_name:1}"
content=$(echo "${body}" | jq -r '.checks.content // ""')
if [ "${content}" = "error" ]; then
  echo "::error::${label} reports published stations with no template: from api, run 'poetry run python scripts/seed_station_templates.py --env ${env_name} --apply' then 'poetry run python scripts/link_stations_to_templates.py --env ${env_name} --apply', then run this again."
  exit 1
fi
if [ -z "${content}" ]; then
  echo "::warning::${label}'s /health has no content check (an older build); the binding was not verified."
fi
