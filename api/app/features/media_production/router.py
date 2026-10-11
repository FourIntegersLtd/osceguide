"""The routes a platform admin uses to produce spoken material: having the agent draft and check
it from a brief, or step by step checking its facts, writing and checking its script, and then
voicing it (narrating a summary as a podcast, re-rendering a slide deck's video, or voicing a
podcast episode). Voicing is refused until the script has been checked.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, error_responses
from app.core.schemas import StationReview
from app.core.tenancy import PlatformAdmin
from app.features.media_production import errors, schemas, service, service_produce

router = APIRouter(tags=["media-production"])


# The refusals any AV production route can return, alongside the shared Forbidden.
_PRODUCTION_ERRORS = (
    errors.ItemNotFound,
    errors.WrongMediaKind,
    errors.AvAlreadyRunning,
    errors.AvUnavailable,
)
# Voicing is also refused for words nobody has checked.
_VOICING_ERRORS = (*_PRODUCTION_ERRORS, errors.ScriptNotChecked)


# Starts checking an item's clinical claims against the guidelines; the result lands in its review.
@router.post(
    "/media/{item_id}/check-facts",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_PRODUCTION_ERRORS),
)
async def check_media_facts(item_id: uuid.UUID, admin: PlatformAdmin, session: Session) -> schemas.MediaRead:
    return await service.enqueue_fact_check(session, item_id, requested_by=admin.user_id)


# Records a fact check a person did themselves, each claim with its source, in place of the platform's.
@router.post(
    "/media/{item_id}/hand-check",
    response_model=schemas.MediaRead,
    responses=error_responses(
        Forbidden,
        errors.ItemNotFound,
        errors.WrongMediaKind,
        errors.AvAlreadyRunning,
        errors.ClaimOutsideItem,
    ),
)
async def record_hand_check(
    item_id: uuid.UUID, body: schemas.HandCheckRequest, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    claims = [claim.model_dump() for claim in body.claims]
    return await service.record_hand_check(session, item_id, claims, checked_by=admin.user_id)


# Starts writing what an item will say and checking it against its source. Nothing is voiced.
@router.post(
    "/media/{item_id}/write-script",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_PRODUCTION_ERRORS),
)
async def write_media_script(
    item_id: uuid.UUID, body: schemas.ScriptWriteRequest, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    return await service.enqueue_script_write(
        session, item_id, requested_by=admin.user_id, rewrite=body.rewrite
    )


# Starts the agent that drafts an item from a brief, checks it and corrects it, stopping before voicing.
@router.post(
    "/media/{item_id}/produce",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, errors.NotEditableError, *_PRODUCTION_ERRORS),
)
async def produce_media(
    item_id: uuid.UUID, body: schemas.ProduceRequest, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    return await service_produce.enqueue_produce(
        session, item_id, requested_by=admin.user_id, brief=body.brief
    )


# Asks a running agent to stop after the step it is on. What it has done so far is kept.
@router.post(
    "/media/{item_id}/stop-produce",
    response_model=schemas.MediaRead,
    responses=error_responses(Forbidden, errors.ItemNotFound),
)
async def stop_producing_media(
    item_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    return await service_produce.stop_produce(session, item_id, requested_by=admin.user_id)


# Starts the agent on a platform station's draft version: it drafts from the brief if asked, checks
# the facts and corrects what the sources contradict. The screen reads progress from the review.
@router.post(
    "/platform/stations/{station_id}/versions/{version}/produce",
    response_model=StationReview,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(
        Forbidden,
        errors.StationNotFound,
        errors.VersionNotFound,
        errors.StationNotEditable,
        errors.StationHasNoTemplate,
        errors.FactCheckRunning,
        errors.StationBeingProduced,
    ),
)
async def produce_station(
    station_id: uuid.UUID, version: int, body: schemas.ProduceRequest, admin: PlatformAdmin, session: Session
) -> StationReview:
    return await service_produce.enqueue_station_produce(
        session,
        station_id,
        version,
        requested_by=admin.user_id,
        brief=body.brief,
    )


# Asks the agent producing a station version to stop after the step it is on.
@router.post(
    "/platform/stations/{station_id}/versions/{version}/stop-produce",
    response_model=StationReview,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, errors.StationNotFound, errors.VersionNotFound),
)
async def stop_producing_station(
    station_id: uuid.UUID, version: int, admin: PlatformAdmin, session: Session
) -> StationReview:
    return await service_produce.stop_station_produce(
        session, station_id, version, requested_by=admin.user_id
    )


# Starts narrating a summary item's text as a two-host podcast episode.
@router.post(
    "/media/{item_id}/generate-podcast",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_VOICING_ERRORS),
)
async def generate_summary_podcast(
    item_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    return await service.enqueue_summary_podcast(session, item_id, requested_by=admin.user_id)


# Starts re-rendering a slide deck's narrated video after its slides have changed.
@router.post(
    "/media/{item_id}/regenerate-av",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_VOICING_ERRORS),
)
async def regenerate_slide_av(
    item_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    return await service.enqueue_slide_regenerate(session, item_id, requested_by=admin.user_id)


# Starts voicing a podcast episode's script into an audio file.
@router.post(
    "/media/{item_id}/generate-audio",
    response_model=schemas.MediaRead,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(Forbidden, *_VOICING_ERRORS),
)
async def generate_podcast_audio(
    item_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.MediaRead:
    return await service.enqueue_podcast_audio(session, item_id, requested_by=admin.user_id)


# Frees an item a dead worker left locked in a running status; the way out when nothing reaps it.
@router.post(
    "/media/{item_id}/unlock",
    response_model=schemas.MediaRead,
    responses=error_responses(Forbidden, errors.ItemNotFound, errors.NotRunning),
)
async def unlock_media(item_id: uuid.UUID, admin: PlatformAdmin, session: Session) -> schemas.MediaRead:
    return await service.release_stuck(session, item_id)
