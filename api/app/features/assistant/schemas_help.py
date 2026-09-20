"""B2C help catalogue and knowledge chat contracts."""

from typing import Literal

from pydantic import BaseModel, Field

ExamCode = Literal["sca", "plab", "casc", "ortho"]


class HelpCategory(BaseModel):
    id: str = ""
    slug: str
    title: str
    description: str = ""
    icon_key: str = "book"
    sort_order: int = 0
    app_types: list[str]
    article_count: int = 0


class HelpArticle(BaseModel):
    id: str = ""
    slug: str
    title: str
    summary: str = ""
    app_types: list[str]
    category_slug: str
    category_title: str = ""
    sort_order: int = 0
    body_md: str
    related_slugs: list[str] = Field(default_factory=list)


class HelpCategories(BaseModel):
    categories: list[HelpCategory]


class HelpArticles(BaseModel):
    articles: list[HelpArticle]


class HelpArticleDetail(BaseModel):
    article: HelpArticle


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class KnowledgeChat(BaseModel):
    app_type: ExamCode = "sca"
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)


class KnowledgeReply(BaseModel):
    reply: str
