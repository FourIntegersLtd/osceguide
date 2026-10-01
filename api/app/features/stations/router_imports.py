"""Station import routes: upload a PDF or Word station document and get drafts back.

An organisation's admins import into their own library and the platform's
admins into the platform's, so every route has a `/platform` twin. Reading and
listing are admin-only too: an import holds the whole document, examiner
material included.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, Unauthenticated, error_responses
from app.core.rate_limit import STATION_IMPORT, TooManyRequests, check
from app.core.tenancy import OrgAdmin, PlatformAdmin
from app.features.stations import errors, schemas, service_imports

router = APIRouter(tags=["stations"])

Session = Annotated[AsyncSession, Depends(get_session)]
ImportFile = Annotated[UploadFile, File(description="The station document, as a PDF or a Word .docx file")]
ExamCode = Annotated[str, Form(min_length=1, max_length=32, description="The exam the station belongs to")]
TemplateVersionId = Annotated[
    uuid.UUID | None,
    Form(description="A published template version to draft the station on. Leave out to draft a template."),
]

_AUTH = (Unauthenticated, Forbidden)
_UPLOAD = (
    errors.InvalidImportFileError,
    errors.UnknownExamError,
    errors.StationTemplateVersionNotFound,
    errors.TemplateNotPublishedError,
    TooManyRequests,
)
_STATION = (
    errors.StationImportNotFound,
    errors.ImportNotReadyError,
    errors.StationTemplateVersionNotFound,
    errors.TemplateNotPublishedError,
    TooManyRequests,
)


# Upload one station document into this org's library and queue its first draft.
@router.post(
    "/orgs/{org_slug}/station-imports",
    response_model=schemas.StationImportRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(Forbidden, *_UPLOAD),
)
async def upload_station_import(
    workspace: OrgAdmin,
    session: Session,
    file: ImportFile,
    exam_code: ExamCode,
    template_version_id: TemplateVersionId = None,
) -> schemas.StationImportRead:
    user_id = workspace.principal.user_id
    await check(STATION_IMPORT, f"user:{user_id}")
    return await service_imports.start_import(
        session,
        workspace.org_id,
        user_id=user_id,
        filename=file.filename or "",
        content=await file.read(),
        exam_code=exam_code,
        template_version_id=template_version_id,
    )


# This org's recent imports, newest first.
@router.get(
    "/orgs/{org_slug}/station-imports",
    response_model=schemas.StationImportList,
    responses=error_responses(Forbidden),
)
async def list_station_imports(workspace: OrgAdmin, session: Session) -> schemas.StationImportList:
    return await service_imports.list_imports(session, workspace.org_id)


# One of this org's imports and how far it has got.
@router.get(
    "/orgs/{org_slug}/station-imports/{import_id}",
    response_model=schemas.StationImportRead,
    responses=error_responses(Forbidden, errors.StationImportNotFound),
)
async def read_station_import(
    import_id: uuid.UUID, workspace: OrgAdmin, session: Session
) -> schemas.StationImportRead:
    return await service_imports.read_import(session, workspace.org_id, import_id)


# Draft the station once the import's template has been published.
@router.post(
    "/orgs/{org_slug}/station-imports/{import_id}/station",
    response_model=schemas.StationImportRead,
    responses=error_responses(Forbidden, *_STATION),
)
async def draft_station_from_import(
    import_id: uuid.UUID, workspace: OrgAdmin, session: Session
) -> schemas.StationImportRead:
    await check(STATION_IMPORT, f"user:{workspace.principal.user_id}")
    return await service_imports.request_station(session, workspace.org_id, import_id)


# Upload one station document into the platform library and queue its first draft.
@router.post(
    "/platform/station-imports",
    response_model=schemas.StationImportRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(*_AUTH, *_UPLOAD),
)
async def upload_platform_station_import(
    admin: PlatformAdmin,
    session: Session,
    file: ImportFile,
    exam_code: ExamCode,
    template_version_id: TemplateVersionId = None,
) -> schemas.StationImportRead:
    await check(STATION_IMPORT, f"user:{admin.user_id}")
    return await service_imports.start_import(
        session,
        None,
        user_id=admin.user_id,
        filename=file.filename or "",
        content=await file.read(),
        exam_code=exam_code,
        template_version_id=template_version_id,
    )


# The platform's recent imports, newest first.
@router.get(
    "/platform/station-imports",
    response_model=schemas.StationImportList,
    responses=error_responses(*_AUTH),
)
async def list_platform_station_imports(admin: PlatformAdmin, session: Session) -> schemas.StationImportList:
    return await service_imports.list_imports(session, None)


# One of the platform's imports and how far it has got.
@router.get(
    "/platform/station-imports/{import_id}",
    response_model=schemas.StationImportRead,
    responses=error_responses(*_AUTH, errors.StationImportNotFound),
)
async def read_platform_station_import(
    import_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.StationImportRead:
    return await service_imports.read_import(session, None, import_id)


# Draft the platform station once the import's template has been published.
@router.post(
    "/platform/station-imports/{import_id}/station",
    response_model=schemas.StationImportRead,
    responses=error_responses(*_AUTH, *_STATION),
)
async def draft_platform_station_from_import(
    import_id: uuid.UUID, admin: PlatformAdmin, session: Session
) -> schemas.StationImportRead:
    await check(STATION_IMPORT, f"user:{admin.user_id}")
    return await service_imports.request_station(session, None, import_id)
