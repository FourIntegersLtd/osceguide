"""Station images, for both scopes.

Both scopes are wiring over one service, differing only in who is allowed to call them and whether
an organisation owns the station.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile

from app.core.db import SessionDep as Session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.settings import SettingsDep
from app.core.tenancy import OrgAdmin, PlatformAdmin
from app.features.stations import errors, schemas, service_photos

router = APIRouter(tags=["stations"])

# The template's media block the images are added to.
MediaBlock = Annotated[
    str, Query(alias="block", min_length=1, max_length=200, description="A media block id")
]

_PHOTO_REFUSALS = (
    errors.VersionNotFound,
    errors.NotEditableError,
    errors.InvalidPhotoError,
    errors.NotAMediaBlockError,
    errors.PhotoNotOnStationError,
    errors.PhotoStorageUnavailable,
)


@router.post(
    "/orgs/{org_slug}/stations/{station_id}/versions/{version}/photos",
    response_model=schemas.StationPhotosResult,
    responses=error_responses(Forbidden, *_PHOTO_REFUSALS),
)
async def add_station_photos(
    station_id: uuid.UUID,
    version: int,
    workspace: OrgAdmin,
    session: Session,
    settings: SettingsDep,
    block_id: MediaBlock,
    files: Annotated[list[UploadFile], File(description="PNG or JPEG images")],
) -> schemas.StationPhotosResult:
    """Put images on one of a station's media blocks.

    The block, not the exam, decides where an image lands. The field name is
    `files`, as the retiring uploader sent it.
    """
    prepared = [(upload.filename or "", upload.size or 0, upload.file) for upload in files]
    read, failed = await service_photos.add_photos(
        session,
        workspace.org_id,
        station_id,
        version,
        block_id=block_id,
        files=prepared,
        settings=settings,
    )
    return schemas.StationPhotosResult(
        version=read,
        uploaded=len(prepared) - len(failed),
        failed=[schemas.PhotoUploadFailure(**failure) for failure in failed],
    )


@router.post(
    "/orgs/{org_slug}/stations/{station_id}/versions/{version}/photos/remove",
    response_model=schemas.StationVersionRead,
    responses=error_responses(Forbidden, *_PHOTO_REFUSALS),
)
async def remove_station_photo(
    station_id: uuid.UUID,
    version: int,
    body: schemas.RemoveStationPhoto,
    workspace: OrgAdmin,
    session: Session,
    settings: SettingsDep,
) -> schemas.StationVersionRead:
    """Take one image off a station, and out of the bucket.

    A POST rather than a DELETE because the URL to remove travels in the body:
    it is long, it is not this resource's identifier, and a query string is
    the wrong place for it.
    """
    return await service_photos.remove_photo(
        session,
        workspace.org_id,
        station_id,
        version,
        url=body.photo_url,
        settings=settings,
    )


@router.post(
    "/platform/stations/{station_id}/versions/{version}/photos",
    response_model=schemas.StationPhotosResult,
    responses=error_responses(Unauthenticated, Forbidden, errors.StationNotFound, *_PHOTO_REFUSALS),
)
async def add_platform_station_photos(
    station_id: uuid.UUID,
    version: int,
    admin: PlatformAdmin,
    session: Session,
    settings: SettingsDep,
    block_id: MediaBlock,
    files: Annotated[list[UploadFile], File(description="PNG or JPEG images")],
) -> schemas.StationPhotosResult:
    """The library's own images, on one of the station's media blocks."""
    _ = admin
    prepared = [(upload.filename or "", upload.size or 0, upload.file) for upload in files]
    read, failed = await service_photos.add_photos(
        session, None, station_id, version, block_id=block_id, files=prepared, settings=settings
    )
    return schemas.StationPhotosResult(
        version=read,
        uploaded=len(prepared) - len(failed),
        failed=[schemas.PhotoUploadFailure(**failure) for failure in failed],
    )


# Take one image off a library station, and out of the bucket.
@router.post(
    "/platform/stations/{station_id}/versions/{version}/photos/remove",
    response_model=schemas.StationVersionRead,
    responses=error_responses(Unauthenticated, Forbidden, errors.StationNotFound, *_PHOTO_REFUSALS),
)
async def remove_platform_station_photo(
    station_id: uuid.UUID,
    version: int,
    body: schemas.RemoveStationPhoto,
    admin: PlatformAdmin,
    session: Session,
    settings: SettingsDep,
) -> schemas.StationVersionRead:
    _ = admin
    return await service_photos.remove_photo(
        session, None, station_id, version, url=body.photo_url, settings=settings
    )
