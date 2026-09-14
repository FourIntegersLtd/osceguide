#!/bin/sh
# Railway / self-hosted: gunicorn health endpoint + one worker subprocess (OSCE_LIVEKIT_WORKER).
# LiveKit Cloud: the worker runs in-process via livekit_cloud_host.
set -e
if [ -n "${RAILWAY_PROJECT_ID}" ] \
  || [ -n "${RAILWAY_ENVIRONMENT}" ] \
  || [ "${OSCE_LIVEKIT_HOSTING}" = "self-hosted" ]; then
  exec make start
fi
exec python hosting/livekit_cloud_host.py start
