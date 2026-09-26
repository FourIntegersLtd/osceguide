"""Station images: uploading them to S3, and taking them off again.

Two guards worth keeping in mind:

- **A fresh key per file.** Keying on `{username}/{original filename}` let two authors uploading
  `xray.png` overwrite one another silently.
- **Delete checks the station first.** Deleting whatever URL was handed would let any authorised
  caller destroy any object in the bucket.

Uploading is allowed on a published version for the same reason correcting the reading brief is (T5):
an image is what a candidate is shown, not what they are marked against. An archived version still
refuses everything.
"""

from __future__ import annotations

import uuid
from typing import BinaryIO

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_mapped
from app.core.settings import Settings
from app.features.media_production import service_storage as storage
from app.features.stations import domain, domain_photos, errors, repository
from app.features.stations.models import StationVersion
from app.features.stations.refusals import REFUSALS as _REFUSALS
from app.features.stations.schemas import StationVersionRead
from app.features.stations.service import _exam_code, read_station
from app.features.stations.service_versions import _version, _version_read


def _ensure_storage(settings: Settings) -> None:
    """Refuse a photo operation outright when no object storage is configured."""
    if not storage.is_configured(settings):
        raise errors.PhotoStorageUnavailable()


async def _editable_version(
    session: AsyncSession, org_id: uuid.UUID | None, station_id: uuid.UUID, version: int
) -> StationVersion:
    """The named version, if its brief may still be edited (T5's rule, shared with photos)."""
    station_version = await _version(session, org_id, station_id, version)
    try:
        domain.ensure_brief_editable(
            domain.VersionRef(number=station_version.version, status=domain.Status(station_version.status))
        )
    except domain.LifecycleError as exc:
        raise_mapped(exc, _REFUSALS)
    return station_version


async def add_photos(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    station_id: uuid.UUID,
    version: int,
    *,
    files: list[tuple[str, int, BinaryIO]],
    settings: Settings,
) -> tuple[StationVersionRead, list[dict[str, str]]]:
    """Put images on a station's version. Returns the version and what failed.

    One bad file does not lose the others: each is validated and uploaded on its own, and the caller
    is told which ones did not make it. A partial success answers 200, with the failures named.
    """
    _ensure_storage(settings)
    station = await read_station(session, org_id, station_id)
    exam_code = await _exam_code(session, station)
    station_version = await _editable_version(session, org_id, station_id, version)

    content = dict(station_version.content or {})
    failed: list[dict[str, str]] = []
    for filename, size, handle in files:
        try:
            domain_photos.validate_upload(filename=filename, size=size)
            # SEC-013: read the leading bytes and rewind, so the extension check
            # above is backed by what the file actually is before it is stored.
            header = handle.read(domain_photos.SNIFF_BYTES)
            handle.seek(0)
            domain_photos.ensure_real_image(header)
        except domain_photos.InvalidPhoto as exc:
            failed.append({"filename": filename, "error": str(exc)})
            continue
        key = domain_photos.object_key(station_id=station_id, filename=filename)
        url = storage.put_object(settings, handle, key)
        content = domain_photos.with_photo(content, url=url, exam_code=exam_code)

    await repository.set_version_content(session, org_id, station_version.id, content=content)
    return _version_read(await _version(session, org_id, station_id, version)), failed


async def remove_photo(
    session: AsyncSession,
    org_id: uuid.UUID | None,
    station_id: uuid.UUID,
    version: int,
    *,
    url: str,
    settings: Settings,
) -> StationVersionRead:
    """Take an image off a station, and out of the bucket.

    The reference is dropped only after the object is gone, so a failed delete
    leaves a station pointing at an image that still exists rather than at one
    that does not.
    """
    _ensure_storage(settings)
    station_version = await _editable_version(session, org_id, station_id, version)

    content = dict(station_version.content or {})
    updated, found = domain_photos.without_photo(content, url=url)
    if not found:
        raise errors.PhotoNotOnStationError()

    storage.remove_object(settings, url)
    await repository.set_version_content(session, org_id, station_version.id, content=updated)
    return _version_read(await _version(session, org_id, station_id, version))
