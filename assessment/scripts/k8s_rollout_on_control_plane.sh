#!/usr/bin/env bash
# Rolls the two workers out to ONE environment (staging or production) on the K3s
# control plane.
#
# Who runs it: the deploy workflows, over SSH (.github/actions/roll-out-workers).
# You can also run it by hand on the control plane:
#
#   ENVIRONMENT=staging K8S_MANIFEST_DIR=/root/k8s/assessment-platform/staging \
#     bash k8s_rollout_on_control_plane.sh
#
# What it expects in K8S_MANIFEST_DIR: a copy of the repo's k8s/base and
# k8s/overlays folders, with the chosen overlay already pinned to an image digest
# by the workflow.
#
# What it never does: create or change secrets. Each namespace's
# assessment-worker-secrets and ghcr-pull-credentials are made by hand once
# (k8s/README.md), because they hold real keys that must not pass through CI.
set -euo pipefail

# Which environment to deploy, e.g. "staging" or "production".
ENVIRONMENT="${ENVIRONMENT:?Set ENVIRONMENT to staging or production}"
# Where the workflow copied the manifests for this environment.
K8S_MANIFEST_DIR="${K8S_MANIFEST_DIR:?Set K8S_MANIFEST_DIR to the folder holding base/ and overlays/}"
# How long to wait for each rollout. Old pods drain their live consultations for up
# to 15 minutes (terminationGracePeriodSeconds: 900), so this must be well above that.
ROLLOUT_TIMEOUT_SECS="${ROLLOUT_TIMEOUT_SECS:-1800}"

# Map each environment to its namespace. Must match the `namespace:` line in
# k8s/overlays/<environment>/kustomization.yaml; tests/test_k8s_config.py checks
# the two agree.
case "$ENVIRONMENT" in
  production) NAMESPACE="assessment-platform" ;;
  staging) NAMESPACE="assessment-platform-staging" ;;
  *)
    echo "Unknown ENVIRONMENT '${ENVIRONMENT}': expected staging or production." >&2
    exit 1
    ;;
esac

OVERLAY_DIR="${K8S_MANIFEST_DIR}/overlays/${ENVIRONMENT}"
[[ -f "${OVERLAY_DIR}/kustomization.yaml" ]] || {
  echo "Missing ${OVERLAY_DIR}/kustomization.yaml: copy k8s/base and k8s/overlays first." >&2
  exit 1
}

# Refuse to deploy into a namespace whose secrets were never created. Without them
# every pod sits in CreateContainerConfigError (worker secrets) or ImagePullBackOff
# (pull secret), and the rollout would only time out 30 minutes later.
for required_secret in assessment-worker-secrets ghcr-pull-credentials; do
  if ! kubectl -n "$NAMESPACE" get secret "$required_secret" >/dev/null 2>&1; then
    echo "Secret ${required_secret} is missing in namespace ${NAMESPACE}." >&2
    echo "Create it by hand first; see k8s/README.md, 'Setting up an environment'." >&2
    exit 1
  fi
done

# Production runs one replica of each worker per labelled node (one pod per node), so
# the replica count is read from the cluster at each rollout; a promote never resets
# it to the base's 1. The overlay file is this deploy's own copy, so appending is safe.
if [[ "$ENVIRONMENT" == "production" ]]; then
  worker_node_count="$(kubectl get nodes -l osceguide.io/livekit-worker=true -o name | wc -l | tr -d '[:space:]')"
  if [[ "${worker_node_count:-0}" -lt 1 ]]; then
    echo "No nodes are labelled osceguide.io/livekit-worker=true: refusing to deploy production with 0 replicas." >&2
    echo "Label a worker node first; see k8s/README.md, 'Node labels'." >&2
    exit 1
  fi
  echo "==> Production replicas = ${worker_node_count} (labelled worker nodes)"
  cat >>"${OVERLAY_DIR}/kustomization.yaml" <<REPLICAS

replicas:
  - name: assessment-worker
    count: ${worker_node_count}
  - name: assistant-worker
    count: ${worker_node_count}
REPLICAS
fi

# Apply everything for this environment in one go: namespace, network policy,
# config maps and both deployments, with the overlay's namespace, image and settings.
echo "==> Applying ${ENVIRONMENT} (namespace ${NAMESPACE})"
kubectl apply -k "$OVERLAY_DIR"

# Wait for each worker to finish rolling. A pod sitting in Terminating for several
# minutes is a consultation draining, not a stuck rollout.
for deployment_name in assessment-worker assistant-worker; do
  kubectl rollout status "deployment/${deployment_name}" -n "$NAMESPACE" --timeout="${ROLLOUT_TIMEOUT_SECS}s"
done

# Show where the pods landed, for the workflow log.
kubectl get pods -n "$NAMESPACE" -o wide
echo "==> ${ENVIRONMENT} rollout complete"
