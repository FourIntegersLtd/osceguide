"""The K8s manifests must declare backends the way those backends actually authenticate,
and the staging and production overlays must stay separate in the ways deploys rely on."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from voice_infra import BackendRegistry

REPO_ROOT = Path(__file__).resolve().parents[1]
K8S_DIR = REPO_ROOT / "k8s"
# The manifests every environment shares (k8s/base) ...
K8S = K8S_DIR / "base"
# ... and what each environment changes on top of them (k8s/overlays/<environment>).
OVERLAYS_DIR = K8S_DIR / "overlays"
ENVIRONMENTS = ("staging", "production")
# The namespace production has always run in. Renaming it would start a second set of
# live workers beside the running ones instead of replacing them.
PRODUCTION_NAMESPACE = "assessment-platform"
WORKER_IMAGE = "ghcr.io/fourintegersltd/osceguide-assessment-platform"
ROLLOUT_SCRIPT = REPO_ROOT / "scripts" / "k8s_rollout_on_control_plane.sh"
CONFIGMAPS = ("configmap.yaml", "configmap-assistant.yaml")
# The headers each backend's worker guard reads: b2c-api worker_guard.py,
# b2b-api http/worker_guard.py, and platform-api core/auth.require_worker_secret.
# All three are declared at once because they coexist for the whole cutover —
# a session already in flight keeps talking to the backend that dispatched it.
EXPECTED_HEADERS = {
    "practice": "X-B2C-Worker-Secret",
    "institution": "X-B2B-Worker-Secret",
    "platform": "X-Worker-Secret",
}


def _backends_json(configmap: str) -> str:
    text = (K8S / configmap).read_text()
    match = re.search(r"VOICE_BACKENDS_JSON: \|\n((?:    .*\n)+)", text)
    assert match, f"{configmap} declares no VOICE_BACKENDS_JSON"
    return "\n".join(line[4:] for line in match.group(1).splitlines())


@pytest.mark.parametrize("configmap", CONFIGMAPS)
def test_configmap_backends_parse_and_use_the_backends_secret_headers(configmap) -> None:
    registry = BackendRegistry.from_json(_backends_json(configmap))
    assert set(registry.labels()) == set(EXPECTED_HEADERS)
    for label, header in EXPECTED_HEADERS.items():
        assert registry.get(label).secret_header == header, f"{configmap}: {label}"


def test_institution_backend_declares_its_prefixed_attempt_routes() -> None:
    for configmap in ("configmap.yaml",):
        institution = BackendRegistry.from_json(_backends_json(configmap)).get("institution")
        assert institution.attempt_path.startswith("/api/b2b/worker/attempts/")
        assert institution.transcript_path.startswith("/api/b2b/worker/attempts/")


@pytest.mark.parametrize("deployment", ("deployment.yaml", "deployment-assistant.yaml"))
def test_deployments_reference_a_published_image(deployment) -> None:
    text = (K8S / deployment).read_text()
    assert "OWNER" not in text
    assert re.search(r"image: ghcr\.io/fourintegersltd/osceguide-assessment-platform[:@]", text)


@pytest.mark.parametrize("deployment", ("deployment.yaml", "deployment-assistant.yaml"))
def test_deployments_reference_the_secret_the_example_defines(deployment) -> None:
    """A secretRef naming anything else leaves the pod in CreateContainerConfigError."""
    secret_name = re.search(r"^\s+name: (\S+)", (K8S_DIR / "secret.example.yaml").read_text(), re.MULTILINE).group(1)
    text = (K8S / deployment).read_text()
    refs = re.findall(r"secretRef:\s*\n\s*name: (\S+)", text)
    assert refs and all(ref == secret_name for ref in refs), (deployment, refs, secret_name)


@pytest.mark.parametrize("deployment", ("deployment.yaml", "deployment-assistant.yaml"))
def test_deployments_schedule_only_onto_labelled_worker_nodes(deployment) -> None:
    """Never the control plane: the same node affinity the legacy worker uses."""
    text = (K8S / deployment).read_text()
    assert "requiredDuringSchedulingIgnoredDuringExecution" in text
    assert "key: osceguide.io/livekit-worker" in text


@pytest.mark.parametrize("deployment", ("deployment.yaml", "deployment-assistant.yaml"))
def test_deployments_run_unprivileged_and_drop_capabilities(deployment) -> None:
    """SEC-010: the pod runs as the image's non-root uid and the container drops
    every capability and cannot escalate privileges."""
    text = (K8S / deployment).read_text()
    assert "runAsNonRoot: true" in text
    assert "runAsUser: 10001" in text
    assert "allowPrivilegeEscalation: false" in text
    assert re.search(r"capabilities:\s*\n\s*drop:\s*\n\s*- ALL", text), deployment
    assert "type: RuntimeDefault" in text


def test_a_network_policy_confines_inbound_traffic_to_the_worker_ports() -> None:
    """SEC-010: only the probe and agent ports are reachable; everything else in
    is denied, and the policy selects both worker deployments."""
    text = (K8S / "networkpolicy.yaml").read_text()
    assert "kind: NetworkPolicy" in text
    assert "- Ingress" in text
    for app in ("assessment-worker", "assistant-worker"):
        assert app in text, app
    for port in ("8080", "8087", "8088"):
        assert f"port: {port}" in text, port


def test_the_platform_backend_serves_the_workers_default_attempt_routes() -> None:
    """The unified backend mounts `/api/worker/attempts/...` unprefixed.

    Declaring the paths anyway would be three more strings to keep in step
    with a router; leaving them out means the worker's own defaults are the
    contract, and this is what says that was deliberate.
    """
    for configmap in CONFIGMAPS:
        platform = BackendRegistry.from_json(_backends_json(configmap)).get("platform")
        assert platform.attempt_path == "/api/worker/attempts/{attempt_id}"
        assert platform.transcript_path == "/api/worker/attempts/{attempt_id}/transcript"
        assert platform.transcript_chunks_path == "/api/worker/attempts/{attempt_id}/transcript-chunks"


def test_every_declared_backend_names_a_secret_the_example_defines() -> None:
    """A label whose env vars are not in the secret leaves the worker unable to
    reach that backend, and the failure only shows up on a dispatch."""
    example = (K8S_DIR / "secret.example.yaml").read_text()
    for configmap in CONFIGMAPS:
        registry = BackendRegistry.from_json(_backends_json(configmap))
        for label in registry.labels():
            backend = registry.get(label)
            assert f"{backend.base_url_env}:" in example, f"{configmap}: {label} base url"
            assert f"{backend.secret_env}:" in example, f"{configmap}: {label} secret"


# --- Staging and production overlays -------------------------------------------------


def _overlay_text(environment: str) -> str:
    return (OVERLAYS_DIR / environment / "kustomization.yaml").read_text()


def _overlay_namespace(environment: str) -> str:
    namespace_match = re.search(r"^namespace: (\S+)$", _overlay_text(environment), re.MULTILINE)
    assert namespace_match, f"{environment} overlay sets no namespace"
    return namespace_match.group(1)


def test_production_keeps_the_live_namespace_and_staging_has_its_own() -> None:
    assert _overlay_namespace("production") == PRODUCTION_NAMESPACE
    assert _overlay_namespace("staging") == "assessment-platform-staging"


def test_base_manifests_name_no_namespace() -> None:
    """The overlay decides the namespace. A namespace written into a base file would
    pin that resource to one environment (and stop the overlay patches matching it)."""
    for manifest_file in sorted(K8S.glob("*.yaml")):
        if manifest_file.name == "kustomization.yaml":
            continue
        assert not re.search(r"^  namespace:", manifest_file.read_text(), re.MULTILINE), manifest_file.name


def test_only_the_overlays_label_errors_with_an_environment() -> None:
    """Base config maps carry no SENTRY_ENVIRONMENT; each overlay sets its own, so a
    staging error can never be filed under production."""
    for configmap in CONFIGMAPS:
        assert "SENTRY_ENVIRONMENT:" not in (K8S / configmap).read_text(), configmap
    for environment in ENVIRONMENTS:
        sentry_labels = re.findall(r'SENTRY_ENVIRONMENT: "(\w+)"', _overlay_text(environment))
        # One label per worker config map (assessment and assistant).
        assert sentry_labels == [environment, environment], (environment, sentry_labels)


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_overlays_carry_the_lines_the_deploy_rewrites(environment) -> None:
    """.github/actions/roll-out-workers swaps these exact lines for the image digest and
    commit it is deploying. If either line drifts, the deploy fails its own render check."""
    overlay = _overlay_text(environment)
    assert f"  - name: {WORKER_IMAGE}\n    newTag: {environment}\n" in overlay
    assert re.search(r"^  osceguide\.io/commit: unpinned$", overlay, re.MULTILINE)
    # The overlay's image name must be the one the deployments use, or the pin is a no-op.
    for deployment in ("deployment.yaml", "deployment-assistant.yaml"):
        assert f"image: {WORKER_IMAGE}:" in (K8S / deployment).read_text(), deployment


def test_the_rollout_script_maps_each_environment_to_its_overlay_namespace() -> None:
    script = ROLLOUT_SCRIPT.read_text()
    for environment in ENVIRONMENTS:
        script_mapping = re.search(rf'^\s+{environment}\) NAMESPACE="([^"]+)"', script, re.MULTILINE)
        assert script_mapping, f"rollout script has no namespace for {environment}"
        assert script_mapping.group(1) == _overlay_namespace(environment), environment


def test_staging_takes_fewer_sessions_than_production() -> None:
    """Staging pods share worker nodes with production's, so staging's per-pod caps must
    stay below the base (production) caps."""
    for configmap, cap_name in (
        ("configmap.yaml", "LIVEKIT_ASSESSMENT_MAX_CONCURRENT_JOBS"),
        ("configmap-assistant.yaml", "LIVEKIT_ASSISTANT_MAX_CONCURRENT_JOBS"),
    ):
        production_cap = re.search(rf'{cap_name}: "(\d+)"', (K8S / configmap).read_text())
        staging_cap = re.search(rf'{cap_name}: "(\d+)"', _overlay_text("staging"))
        assert production_cap and staging_cap, cap_name
        assert int(staging_cap.group(1)) < int(production_cap.group(1)), cap_name


@pytest.mark.skipif(shutil.which("kubectl") is None, reason="kubectl is not installed")
@pytest.mark.parametrize(
    ("environment", "expected_namespace", "expected_replicas"),
    (("staging", "assessment-platform-staging", 1), ("production", PRODUCTION_NAMESPACE, 3)),
)
def test_each_overlay_renders_into_its_own_namespace(environment, expected_namespace, expected_replicas) -> None:
    """Render the overlay exactly as `kubectl apply -k` would and check what the cluster receives."""
    rendered = subprocess.run(
        ["kubectl", "kustomize", str(OVERLAYS_DIR / environment)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    rendered_namespaces = set(re.findall(r"^  namespace: (\S+)$", rendered, re.MULTILINE))
    assert rendered_namespaces == {expected_namespace}
    # The Namespace object itself is renamed too, so staging never creates production's.
    assert re.search(rf"^kind: Namespace\nmetadata:\n(?:  .*\n)*?  name: {expected_namespace}$", rendered, re.MULTILINE)
    assert f"image: {WORKER_IMAGE}:{environment}" in rendered
    assert re.findall(r"^  replicas: (\d+)$", rendered, re.MULTILINE) == [str(expected_replicas)] * 2
    assert f'SENTRY_ENVIRONMENT: {environment}' in rendered
