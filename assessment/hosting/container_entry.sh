#!/bin/sh
# Self-hosted (K8s): gunicorn health endpoint + one worker subprocess (OSCE_LIVEKIT_WORKER).
# LiveKit Cloud: the worker runs in-process via livekit_cloud_host.
set -e
if [ "${OSCE_LIVEKIT_HOSTING}" = "self-hosted" ]; then
  exec make start
fi
exec python hosting/livekit_cloud_host.py start
