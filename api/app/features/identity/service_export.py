"""A person's own data, as one JSON download (E-5).

UK GDPR gives a month to answer a subject access request; this route answers
it immediately, self-serve, by reusing the services the rest of the app
already reads through — no new read model, no new layer. It intentionally
does not aggregate an institution's decision about the person (that is the
organisation's record, not something this route can hand over on the
person's say-so alone); it is everything this account owns: its own profile,
its own attempts with their transcripts and marks, and its own payments.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import service_privacy as attempts_privacy
from app.features.billing import service_receipts as billing_receipts
from app.features.identity import repository
from app.features.identity.errors import AccountNotFound
from app.features.identity.schemas import (
    ExportedAttempt,
    ExportedPayment,
    ExportedProfile,
    ExportedResult,
    ExportedTranscript,
    ExportedTranscriptMessage,
    MyDataExport,
)


async def export_my_data(session: AsyncSession, *, user_id: uuid.UUID) -> MyDataExport:
    """Everything `user_id` owns, ready to serialise as the export download.

    Raises `AccountNotFound` if the account is gone — a closed account can still
    sign in during the 30-day window before erasure, so this stays reachable
    right up until the erasure job runs.
    """
    user = await repository.user_by_id(session, user_id)
    if user is None:
        raise AccountNotFound()

    attempts = await attempts_privacy.export_for_user(session, user_id)
    payments = await billing_receipts.export_payments_for_user(session, user_id)

    return MyDataExport(
        profile=ExportedProfile(
            id=user.id,
            email=user.email,
            name=user.name,
            exam_code=user.exam_code,
            exam_date=user.exam_date,
            created_at=user.created_at,
        ),
        attempts=[
            ExportedAttempt(
                id=attempt["id"],
                kind=attempt["kind"],
                status=attempt["status"],
                started_at=attempt["started_at"],
                completed_at=attempt["completed_at"],
                transcript=ExportedTranscript(
                    complete=attempt["transcript"]["complete"],
                    messages=[
                        ExportedTranscriptMessage(**message) for message in attempt["transcript"]["messages"]
                    ],
                ),
                results=[ExportedResult(**result) for result in attempt["results"]],
            )
            for attempt in attempts
        ],
        payments=[ExportedPayment(**payment) for payment in payments],
    )
