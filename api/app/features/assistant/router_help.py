"""Help browser endpoints used by all exam help docks."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentPrincipal
from app.core.db import get_session
from app.core.errors import NotFound, Unauthenticated, error_responses
from app.core.ports import ClockDep, VectorIndex
from app.core.settings import SettingsDep
from app.features.assistant import schemas as schemas
from app.features.assistant import service_help, service_knowledge

router = APIRouter(tags=["assistant"])


@router.get(
    "/help/categories",
    response_model=schemas.HelpCategories,
    responses=error_responses(Unauthenticated),
)
async def categories(
    principal: CurrentPrincipal, exam_code: schemas.ExamCode = "sca"
) -> schemas.HelpCategories:
    return schemas.HelpCategories(categories=service_help.list_categories(exam_code))


@router.get(
    "/help/articles",
    response_model=schemas.HelpArticles,
    responses=error_responses(Unauthenticated),
)
async def articles(
    principal: CurrentPrincipal, exam_code: schemas.ExamCode = "sca", category: str | None = None
) -> schemas.HelpArticles:
    return schemas.HelpArticles(articles=service_help.list_articles(exam_code, category))


@router.get(
    "/help/articles/{slug}",
    response_model=schemas.HelpArticleDetail,
    responses=error_responses(NotFound, Unauthenticated),
)
async def article(
    slug: str, principal: CurrentPrincipal, exam_code: schemas.ExamCode = "sca"
) -> schemas.HelpArticleDetail:
    return schemas.HelpArticleDetail(article=service_help.read_article(slug, exam_code))


# Answer a study question grounded in the summaries this learner can access.
@router.post(
    "/help/knowledge-chat",
    response_model=schemas.KnowledgeReply,
    responses=error_responses(Unauthenticated, service_knowledge.KnowledgeUnavailable),
)
async def knowledge_chat(
    body: schemas.KnowledgeChat,
    principal: CurrentPrincipal,
    session: Annotated[AsyncSession, Depends(get_session)],
    clock: ClockDep,
    settings: SettingsDep,
    index: Annotated[VectorIndex, Depends(service_knowledge.get_vector_index)],
) -> schemas.KnowledgeReply:
    return await service_knowledge.answer(
        session, body, user_id=principal.user_id, now=clock.now(), index=index, settings=settings
    )
