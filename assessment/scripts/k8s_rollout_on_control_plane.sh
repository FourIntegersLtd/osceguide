#!/usr/bin/env bash
# Run on the K3s control plane (via CI SSH) after the manifests are copied to K8S_MANIFEST_DIR.
# Applies both workers; secrets (secret.yaml) are created by hand once, never by CI.
set -euo pipefail

K8S_MANIFEST_DIR="${K8S_MANIFEST_DIR:-$HOME/k8s/assessment-platform}"
NAMESPACE="assessment-platform"
ROLLOUT_TIMEOUT_SECS="${ROLLOUT_TIMEOUT_SECS:-600}"

for f in namespace.yaml configmap.yaml configmap-assistant.yaml deployment.yaml deployment-assistant.yaml; do
  [[ -f "${K8S_MANIFEST_DIR}/${f}" ]] || { echo "Missing ${K8S_MANIFEST_DIR}/${f}" >&2; exit 1; }
done

echo "==> Applying namespace, configmaps, deployments"
kubectl apply -f "${K8S_MANIFEST_DIR}/namespace.yaml"
kubectl apply -f "${K8S_MANIFEST_DIR}/configmap.yaml" -f "${K8S_MANIFEST_DIR}/configmap-assistant.yaml"
kubectl apply -f "${K8S_MANIFEST_DIR}/deployment.yaml" -f "${K8S_MANIFEST_DIR}/deployment-assistant.yaml"
for d in assessment-worker assistant-worker; do
  kubectl rollout status "deployment/${d}" -n "$NAMESPACE" --timeout="${ROLLOUT_TIMEOUT_SECS}s"
done
kubectl get pods -n "$NAMESPACE" -o wide
echo "==> K8s rollout complete"
