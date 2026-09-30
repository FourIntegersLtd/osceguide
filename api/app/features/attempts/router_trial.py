"""Trial-marking a rubric version against a sample transcript, streamed (plan §8, Stage 4).

In the attempts slice because marking is: the evaluator and the engine
adapter live here. The rubric doors stay the rubric's: an org admin trials the
org's own versions, a platform admin the platform's, with the same auth as
authoring them. The body is a POST, so a browser reads the stream with
`fetch`, not `EventSource`.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated
from app.core.openapi import sse_responses
from app.core.ports import Evaluator
from app.core.rate_limit import TooManyRequests
from app.core.sse import MEDIA_TYPE, SSE_HEADERS
from app.core.tenancy import OrgAdmin, PlatformAdmin
from app.features.attempts import schemas, service_trial

router = APIRouter(tags=["rubrics"])

Session = Annotated[AsyncSession, Depends(get_session)]
TrialEvaluator = Annotated[Evaluator, Depends(service_trial.trial_evaluator)]


def _trial_responses() -> dict[int | str, dict[str, Any]]:
    """The stream's frame and every refusal made before it opens.

    `model` registers `TrialMarkRead` in the document: no `GET` returns it, so
    the `$ref` `sse_responses` writes would otherwise dangle.
    """
    responses = sse_responses(
        schemas.TrialMarkRead,
        Unauthenticated,
        Forbidden,
        TooManyRequests,
        *service_trial.REFUSALS,
    )
    responses[200]["model"] = schemas.TrialMarkRead
    responses[200]["description"] = (
        "An SSE stream: `connected`, then a `snapshot` frame whose `data` is a `TrialMarkRead` "
        "every five seconds while `marking`, and one last `marked` or `failed` snapshot, then it closes."
    )
    return responses


# Trial-mark one of this organisation's rubric versions (a draft included); streams progress, stores nothing.
@router.post(
    "/orgs/{org_slug}/rubrics/{rubric_id}/versions/{version}/trial",
    responses=_trial_responses(),
    response_class=StreamingResponse,
)
async def trial_org_rubric_version(
    rubric_id: uuid.UUID,
    version: int,
    body: schemas.TrialMarkRequest,
    workspace: OrgAdmin,
    session: Session,
    evaluator: TrialEvaluator,
) -> StreamingResponse:
    plan = await service_trial.prepare_trial(
        session,
        workspace.org_id,
        rubric_id=rubric_id,
        version=version,
        transcript=body.transcript,
        attempt_id=body.attempt_id,
        rate_key=f"org:{workspace.org_id}",
    )
    return StreamingResponse(
        service_trial.trial_stream(plan, evaluator), media_type=MEDIA_TYPE, headers=SSE_HEADERS
    )


# Trial-mark one of the platform's rubric versions (a draft included); streams progress, stores nothing.
@router.post(
    "/platform/rubrics/{rubric_id}/versions/{version}/trial",
    responses=_trial_responses(),
    response_class=StreamingResponse,
)
async def trial_platform_rubric_version(
    rubric_id: uuid.UUID,
    version: int,
    body: schemas.TrialMarkRequest,
    admin: PlatformAdmin,
    session: Session,
    evaluator: TrialEvaluator,
) -> StreamingResponse:
    plan = await service_trial.prepare_trial(
        session,
        None,
        rubric_id=rubric_id,
        version=version,
        transcript=body.transcript,
        attempt_id=body.attempt_id,
        rate_key=f"user:{admin.user_id}",
    )
    return StreamingResponse(
        service_trial.trial_stream(plan, evaluator), media_type=MEDIA_TYPE, headers=SSE_HEADERS
    )
