"""Transcript capture and one-shot delivery for sessions that keep a record (help)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from osce_assessment.contracts import MessageRole, Transcript, TranscriptMessage
from voice_infra import BackendEndpoints
from voice_infra.backend_http import post_json

logger = logging.getLogger(__name__)

RETRY_DELAYS_S = (0.0, 2.0, 5.0, 10.0)
POST_TIMEOUT_S = 30.0
GPT_LIVE_LATE_ITEMS_S = 2.0


class TranscriptRecorder:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.messages: list[TranscriptMessage] = []

    def add(self, role: MessageRole, text: str) -> TranscriptMessage:
        message = TranscriptMessage(role=role, message=text, timestamp=datetime.now(timezone.utc), message_id=str(uuid.uuid4()), seq=len(self.messages))
        self.messages.append(message)
        return message

    def transcript(self) -> Transcript:
        return Transcript(attempt_id=self.session_id, messages=tuple(self.messages), complete=True, runtime_label="livekit-assistant")


class TranscriptDelivery:
    """Posts the transcript once; a failed delivery stays undelivered so the other path retries."""

    def __init__(self, endpoints: BackendEndpoints, recorder: TranscriptRecorder, *, worker_type: str, candidate_ref: str, sleep=asyncio.sleep) -> None:
        self._endpoints = endpoints
        self._recorder = recorder
        self._worker_type = worker_type
        self._candidate_ref = candidate_ref
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self.delivered = False

    async def deliver_once(self, *, settle_s: float = 0.0) -> bool:
        async with self._lock:
            if self.delivered:
                return True
            if settle_s:
                await self._sleep(settle_s)
            url = self._endpoints.assistant_transcript_url(self._recorder.session_id)
            payload = {
                "session_id": self._recorder.session_id,
                "worker_type": self._worker_type,
                "candidate_ref": self._candidate_ref,
                "transcript": self._recorder.transcript().model_dump(mode="json"),
            }
            for attempt, delay in enumerate(RETRY_DELAYS_S):
                if delay:
                    await self._sleep(delay)
                try:
                    status = await post_json(url, payload, headers=self._endpoints.secret_headers(), timeout=POST_TIMEOUT_S)
                except Exception as exc:  # noqa: BLE001 — retried
                    logger.error("transcript POST failed attempt=%s: %s", attempt + 1, exc)
                    continue
                if 200 <= status < 300:
                    self.delivered = True
                    logger.info("transcript delivered session=%s turns=%s attempt=%s", self._recorder.session_id, len(self._recorder.messages), attempt + 1)
                    return True
                logger.warning("transcript POST status=%s attempt=%s", status, attempt + 1)
            logger.error("transcript POST exhausted retries session=%s", self._recorder.session_id)
            return False
