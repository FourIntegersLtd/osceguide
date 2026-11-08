"""Help browser endpoints used by all exam help docks."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentPrincipal
from app.core.db import SessionDep, SessionOpenerDep
from app.core.errors import NotFound, Unauthenticated, error_responses
from app.core.jobs import allow_long_idle
from app.core.ports import ClockDep, GuidelineIndex
from app.core.rate_limit import AI_SPEND, TooManyRequests, per_user
from app.core.settings import SettingsDep
from app.features.assistant import schemas as schemas
from app.features.assistant import service_help, service_knowledge

router = APIRouter(tags=["assistant"])


# List the help categories for one exam. With no exam, only the ones written for every exam.
@router.get(
    "/help/categories",
    response_model=schemas.HelpCategories,
    responses=error_responses(Unauthenticated),
)
async def categories(
    principal: CurrentPrincipal, exam_code: schemas.HelpExamCode | None = None
) -> schemas.HelpCategories:
    return schemas.HelpCategories(categories=service_help.list_categories(exam_code))


# List the help articles for one exam, optionally in one category or matching a search.
@router.get(
    "/help/articles",
    response_model=schemas.HelpArticles,
    responses=error_responses(Unauthenticated),
)
async def articles(
    principal: CurrentPrincipal,
    exam_code: schemas.HelpExamCode | None = None,
    category: str | None = None,
    search: Annotated[
        str | None, Query(max_length=300, description="A fragment of a title or a body.")
    ] = None,
) -> schemas.HelpArticles:
    return schemas.HelpArticles(articles=service_help.list_articles(exam_code, category, search))


# Read one help article.
@router.get(
    "/help/articles/{slug}",
    response_model=schemas.HelpArticleDetail,
    responses=error_responses(NotFound, Unauthenticated),
)
async def article(
    slug: str, principal: CurrentPrincipal, exam_code: schemas.HelpExamCode | None = None
) -> schemas.HelpArticleDetail:
    return schemas.HelpArticleDetail(article=service_help.read_article(slug, exam_code))


# Answer a study question from the learner's stations and summaries, then clinical guidelines.
@router.post(
    "/help/knowledge-chat",
    response_model=schemas.KnowledgeReply,
    responses=error_responses(TooManyRequests, Unauthenticated, service_knowledge.KnowledgeUnavailable),
    dependencies=[Depends(per_user(AI_SPEND))],
)
async def knowledge_chat(
    body: schemas.KnowledgeChat,
    principal: CurrentPrincipal,
    opener: SessionOpenerDep,
    session: SessionDep,
    clock: ClockDep,
    settings: SettingsDep,
    index: Annotated[service_knowledge.MaterialSearch | None, Depends(service_knowledge.get_material_index)],
    guidelines: Annotated[GuidelineIndex | None, Depends(service_knowledge.get_guideline_index)],
) -> schemas.KnowledgeReply:
    # The request session (opened by the sign-in check) may hold a transaction across the model call.
    await allow_long_idle(session)
    return await service_knowledge.answer(
        opener,
        body,
        user_id=principal.user_id,
        now=clock.now(),
        index=index,
        guidelines=guidelines,
        settings=settings,
    )
