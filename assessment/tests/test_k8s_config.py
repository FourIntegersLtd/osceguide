"""The K8s manifests must declare backends the way those backends actually authenticate."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from voice_infra import BackendRegistry

K8S = Path(__file__).resolve().parents[1] / "k8s"
CONFIGMAPS = ("configmap.yaml", "configmap-assistant.yaml")
# The headers the two backends' worker guards read (b2c-api worker_guard.py, b2b-api http/worker_guard.py).
EXPECTED_HEADERS = {"practice": "X-B2C-Worker-Secret", "institution": "X-B2B-Worker-Secret"}


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
