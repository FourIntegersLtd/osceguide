"""The K8s manifests must declare backends the way those backends actually authenticate."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from voice_infra import BackendRegistry

K8S = Path(__file__).resolve().parents[1] / "k8s"
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
    secret_name = re.search(r"^\s+name: (\S+)", (K8S / "secret.example.yaml").read_text(), re.MULTILINE).group(1)
    text = (K8S / deployment).read_text()
    refs = re.findall(r"secretRef:\s*\n\s*name: (\S+)", text)
    assert refs and all(ref == secret_name for ref in refs), (deployment, refs, secret_name)


@pytest.mark.parametrize("deployment", ("deployment.yaml", "deployment-assistant.yaml"))
def test_deployments_schedule_only_onto_labelled_worker_nodes(deployment) -> None:
    """Never the control plane: the same node affinity the legacy worker uses."""
    text = (K8S / deployment).read_text()
    assert "requiredDuringSchedulingIgnoredDuringExecution" in text
    assert "key: osceguide.io/livekit-worker" in text


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
    example = (K8S / "secret.example.yaml").read_text()
    for configmap in CONFIGMAPS:
        registry = BackendRegistry.from_json(_backends_json(configmap))
        for label in registry.labels():
            backend = registry.get(label)
            assert f"{backend.base_url_env}:" in example, f"{configmap}: {label} base url"
            assert f"{backend.secret_env}:" in example, f"{configmap}: {label} secret"
