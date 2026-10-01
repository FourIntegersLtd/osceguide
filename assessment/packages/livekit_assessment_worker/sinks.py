"""Transcript delivery to the dispatching backend over HTTP.

Every turn is streamed as a chunk (best effort; failures are logged and the
interaction continues). The completed transcript is posted once; a non-2xx
status raises so the runtime's retry schedule applies. Route paths come from
the backend's endpoints, so a backend mounted under a prefix needs no code.
"""

from __future__ import annotations

import logging

from osce_assessment.contracts import Transcript, TranscriptMessage
from voice_infra import BackendEndpoints
from voice_infra.backend_http import post_json

logger = logging.getLogger(__name__)


class DeliveryRejected(RuntimeError):
    """The backend answered the completed transcript with a non-2xx status."""

    def __init__(self, status: int) -> None:
        super().__init__(f"transcript delivery returned HTTP {status}")
        self.status = status


class HttpTranscriptSink:
    """Sends transcript turns and the finished transcript to the backend over HTTP."""

    def __init__(self, endpoints: BackendEndpoints, *, chunk_timeout: float = 5.0, transcript_timeout: float = 30.0) -> None:
        self._endpoints = endpoints
        self._chunk_timeout = chunk_timeout
        self._transcript_timeout = transcript_timeout

    async def append(self, attempt_id: str, message: TranscriptMessage) -> None:
        """Post one turn to the backend; a failure is logged and not raised."""
        url = self._endpoints.transcript_chunks_url(attempt_id)
        payload = {"attempt_id": attempt_id, "message": message.model_dump(mode="json")}
        status = await post_json(url, payload, headers=self._endpoints.secret_headers(), timeout=self._chunk_timeout)
        if not 200 <= status < 300:
            logger.warning("[transcript] chunk seq=%s rejected with HTTP %s", message.seq, status)

    async def complete(self, attempt_id: str, transcript: Transcript) -> None:
        """Post the completed transcript; a non-2xx status raises ``DeliveryRejected``."""
        url = self._endpoints.transcript_url(attempt_id)
        payload = {"attempt_id": attempt_id, "transcript": transcript.model_dump(mode="json")}
        status = await post_json(url, payload, headers=self._endpoints.secret_headers(), timeout=self._transcript_timeout)
        if not 200 <= status < 300:
            raise DeliveryRejected(status)
        logger.info("[transcript] delivered attempt=%s turns=%s status=%s", attempt_id, len(transcript.messages), status)
