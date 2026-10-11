"""The platform-admin routes that call an LLM to draft a station, summary, blog post, slide
deck or podcast script for the content team to review before publishing.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, error_responses
from app.core.settings import SettingsDep
from app.core.tenancy import PlatformAdmin
from app.features.generation import schemas, service
from app.features.generation.errors import GenerationEmpty, GenerationUnavailable

router = APIRouter(tags=["generation"])


# Drafts a new station from a free-text prompt, with the prompt the exam's settings (or subtype) name.
@router.post(
    "/platform/generate/station",
    response_model=schemas.GenerateResult,
    responses=error_responses(Forbidden, GenerationUnavailable),
)
async def generate_station(
    body: schemas.GenerateStationRequest,
    admin: PlatformAdmin,
    settings: SettingsDep,
    session: Session,
) -> schemas.GenerateResult:
    _ = admin
    content = await service.generate_station(
        prompt=body.prompt,
        exam_code=body.exam_code,
        session=session,
        station_subtype=body.station_subtype,
        settings=settings,
    )
    return schemas.GenerateResult(content=content)


# Drafts a condition summary from a free-text prompt.
@router.post(
    "/platform/generate/summary",
    response_model=schemas.GenerateResult,
    responses=error_responses(Forbidden, GenerationUnavailable),
)
async def generate_summary(
    body: schemas.GenerateTextRequest,
    admin: PlatformAdmin,
    settings: SettingsDep,
    session: Session,
) -> schemas.GenerateResult:
    _ = admin
    content = await service.generate_summary(
        prompt=body.prompt,
        exam_code=body.exam_code,
        session=session,
        settings=settings,
    )
    return schemas.GenerateResult(content=content)


# Drafts a blog post from a free-text prompt.
@router.post(
    "/platform/generate/blog",
    response_model=schemas.GenerateResult,
    responses=error_responses(Forbidden, GenerationUnavailable),
)
async def generate_blog(
    body: schemas.GenerateTextRequest,
    admin: PlatformAdmin,
    settings: SettingsDep,
    session: Session,
) -> schemas.GenerateResult:
    _ = admin
    content = await service.generate_blog(
        prompt=body.prompt,
        exam_code=body.exam_code,
        session=session,
        settings=settings,
    )
    return schemas.GenerateResult(content=content)


# Drafts a slide deck from a free-text prompt.
@router.post(
    "/platform/generate/slide-deck",
    response_model=schemas.GenerateResult,
    responses=error_responses(Forbidden, GenerationUnavailable, GenerationEmpty),
)
async def generate_slide_deck(
    body: schemas.GenerateTextRequest,
    admin: PlatformAdmin,
    settings: SettingsDep,
    _session: Session,
) -> schemas.GenerateResult:
    _ = admin
    content = await service.generate_slide_deck(
        prompt=body.prompt, exam_code=body.exam_code, settings=settings
    )
    return schemas.GenerateResult(content=content)


# Drafts a podcast script from source material given as a free-text prompt.
@router.post(
    "/platform/generate/podcast",
    response_model=schemas.GenerateResult,
    responses=error_responses(Forbidden, GenerationUnavailable),
)
async def generate_podcast(
    body: schemas.GenerateTextRequest,
    admin: PlatformAdmin,
    settings: SettingsDep,
    _session: Session,
) -> schemas.GenerateResult:
    _ = admin
    content = await service.generate_podcast(prompt=body.prompt, exam_code=body.exam_code, settings=settings)
    return schemas.GenerateResult(content=content)
