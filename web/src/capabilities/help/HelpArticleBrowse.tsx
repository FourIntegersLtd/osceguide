"use client";

import { HiOutlineChevronRight } from "react-icons/hi2";
import { useState } from "react";
import { IoArrowBack } from "react-icons/io5";
import {
  LuBookOpen,
  LuCalendar,
  LuMessageSquare,
  LuRocket,
  LuSearch,
  LuSettings,
  LuShield,
  LuUser,
  LuWallet,
} from "react-icons/lu";
import type { IconType } from "react-icons";
import MarkdownRenderer from "@/foundation/ui/MarkdownRenderer";
import mdStyles from "@/foundation/ui/markdown.module.css";
import { helpType } from "@/foundation/ui/helpType";
import {
  fetchHelpArticle,
  fetchHelpArticles,
  fetchHelpCategories,
  type HelpArticle,
  type HelpCategory,
} from "@/capabilities/help/api";
import {
  B2CPanelCard,
  B2CPanelCardHeader,
} from "@/foundation/ui/B2CPanelCard";
import { useAsync, useSearchQuery } from "@/foundation/hooks";
import { AsyncBoundary } from "@/foundation/ui/AsyncBoundary";

type BrowseView =
  | { name: "browse" }
  | {
      name: "category";
      slug: string;
      title?: string;
      description?: string;
    }
  | { name: "article"; slug: string; fromCategory?: string };

function helpCategoryIcon(iconKey: string): IconType {
  switch (iconKey) {
    case "rocket":
      return LuRocket;
    case "calendar":
      return LuCalendar;
    case "wallet":
      return LuWallet;
    case "message":
      return LuMessageSquare;
    case "shield":
      return LuShield;
    case "settings":
      return LuSettings;
    case "user":
      return LuUser;
    case "book":
    default:
      return LuBookOpen;
  }
}

/** `initialArticle` opens straight on one article, as when Athena suggests it. */
export default function HelpArticleBrowse({
  examCode,
  initialArticle,
}: {
  examCode?: string;
  initialArticle?: string;
}) {
  const [view, setView] = useState<BrowseView>(
    initialArticle ? { name: "article", slug: initialArticle } : { name: "browse" },
  );

  const goBack = () => {
    if (view.name === "article" && view.fromCategory) {
      setView({ name: "category", slug: view.fromCategory });
      return;
    }
    if (view.name === "article") {
      setView({ name: "browse" });
      return;
    }
    if (view.name === "category") {
      setView({ name: "browse" });
    }
  };

  const showBack = view.name !== "browse";

  return (
    <div className="w-full">
      {showBack ? (
        <button
          type="button"
          onClick={goBack}
          className="mb-1 -ml-1 inline-flex h-8 w-8 items-center justify-center rounded-md text-osce-ink-500 transition hover:bg-osce-border-light hover:text-osce-ink-900"
          aria-label="Back"
        >
          <IoArrowBack className="h-5 w-5" />
        </button>
      ) : null}

      {view.name === "browse" ? (
        <BrowsePanel
          examCode={examCode}
          onOpenCategory={(slug, title, description) =>
            setView({ name: "category", slug, title, description })
          }
          onOpenArticle={(slug) =>
            setView({ name: "article", slug })
          }
        />
      ) : null}
      {view.name === "category" ? (
        <CategoryPanel
          key={view.slug}
          examCode={examCode}
          categorySlug={view.slug}
          title={view.title}
          description={view.description}
          onOpenArticle={(slug) =>
            setView({
              name: "article",
              slug,
              fromCategory: view.slug,
            })
          }
        />
      ) : null}
      {view.name === "article" ? (
        <ArticlePanel
          key={view.slug}
          examCode={examCode}
          slug={view.slug}
          onOpenArticle={(slug) =>
            setView({
              name: "article",
              slug,
              fromCategory: view.fromCategory,
            })
          }
        />
      ) : null}
    </div>
  );
}

/** A slug said as words, for a related guide whose title could not be read. */
function readableSlug(slug: string): string {
  return slug.replace(/-/g, " ");
}

/** A list of guides, each a row that opens the guide. */
function ArticleRows({
  articles,
  showCategory = false,
  onOpenArticle,
}: {
  articles: HelpArticle[];
  /** Search results come from every topic, so each row says which one. */
  showCategory?: boolean;
  onOpenArticle: (slug: string) => void;
}) {
  return (
    <ul>
      {articles.map((article) => (
        <li
          key={article.id || article.slug}
          className="border-b border-osce-border-light last:border-b-0"
        >
          <button
            type="button"
            onClick={() => onOpenArticle(article.slug)}
            className="flex w-full items-start gap-3 px-4 py-3.5 text-left transition hover:bg-b2c-surface-muted"
          >
            <span className="min-w-0 flex-1">
              <span className={`block ${helpType.rowTitle}`}>{article.title}</span>
              {article.summary ? (
                <span className={`mt-0.5 block ${helpType.support}`}>{article.summary}</span>
              ) : null}
              {showCategory && article.category_title ? (
                <span className="mt-1 block text-osce-meta text-osce-ink-400">
                  {article.category_title}
                </span>
              ) : null}
            </span>
            <HiOutlineChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-osce-ink-400" />
          </button>
        </li>
      ))}
    </ul>
  );
}

/** The first screen: a search box, then either the matches or the list of topics. */
function BrowsePanel({
  examCode,
  onOpenCategory,
  onOpenArticle,
}: {
  examCode?: string;
  onOpenCategory: (slug: string, title: string, description: string) => void;
  onOpenArticle: (slug: string) => void;
}) {
  const [searchQuery, setSearchQuery] = useState("");
  // What the server is asked for: the box, once typing pauses.
  const query = useSearchQuery(searchQuery);
  const categories = useAsync(() => fetchHelpCategories(examCode), [examCode]);
  // The match is the server's: title, summary and category, searched in SQL
  // rather than by holding every article and filtering it in the browser.
  const search = useAsync(
    () =>
      query.length === 0
        ? Promise.resolve<HelpArticle[]>([])
        : fetchHelpArticles(examCode, undefined, query),
    [examCode, query],
  );

  const searchingCard = (
    <B2CPanelCard>
      <B2CPanelCardHeader>Searching…</B2CPanelCardHeader>
    </B2CPanelCard>
  );

  return (
    <div className="w-full pb-2">
      <h3 className={helpType.title}>
        Help topics
      </h3>
      <p className={`mt-0.5 ${helpType.support}`}>
        Search guides or browse by category
      </p>

      <label className="relative mt-4 block">
        <span className="sr-only">Search help guides</span>
        <LuSearch
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-osce-ink-400"
          aria-hidden
        />
        <input
          type="search"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Search guides, e.g. Create Session"
          className="w-full rounded-xl border border-osce-border py-2.5 pl-9 pr-3 text-osce-body text-osce-ink-900 outline-none placeholder:text-osce-ink-400 focus:border-osce-accent-light focus:ring-2 focus:ring-osce-accent-muted"
        />
      </label>

      <div className="mt-4">
        {query.length > 0 ? (
          <AsyncBoundary state={search} loading={searchingCard}>
            {(results) =>
              search.loading ? (
                searchingCard
              ) : (
                <B2CPanelCard>
                  <B2CPanelCardHeader>
                    {results.length > 0
                      ? `${results.length} result${results.length === 1 ? "" : "s"}`
                      : "No results"}
                  </B2CPanelCardHeader>
                  {results.length === 0 ? (
                    <p className={`px-4 py-4 ${helpType.support}`}>
                      Try different words or browse categories below.
                    </p>
                  ) : (
                    <ArticleRows articles={results} showCategory onOpenArticle={onOpenArticle} />
                  )}
                </B2CPanelCard>
              )
            }
          </AsyncBoundary>
        ) : (
          <AsyncBoundary
            state={categories}
            loading={<p className="py-8 text-osce-body text-osce-ink-500">Loading topics…</p>}
          >
            {(topics) => (
              <B2CPanelCard>
                <B2CPanelCardHeader>Documentation</B2CPanelCardHeader>
                {topics.length === 0 ? (
                  <p className="px-4 py-4 text-osce-body text-osce-ink-500">No help topics yet.</p>
                ) : (
                  <ul>
                    {topics.map((category) => {
                      const Icon = helpCategoryIcon(category.icon_key);
                      return (
                        <li
                          key={category.id || category.slug}
                          className="border-b border-osce-border-light last:border-b-0"
                        >
                          <button
                            type="button"
                            onClick={() =>
                              onOpenCategory(category.slug, category.title, category.description)
                            }
                            className="flex w-full items-start gap-3 px-4 py-3.5 text-left transition hover:bg-b2c-surface-muted"
                          >
                            <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-osce-accent-muted text-osce-accent">
                              <Icon className="h-4 w-4" aria-hidden />
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className={`block ${helpType.rowTitle}`}>{category.title}</span>
                              <span className={`mt-0.5 block ${helpType.support}`}>
                                {category.description}
                              </span>
                            </span>
                            <HiOutlineChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-osce-ink-400" />
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </B2CPanelCard>
            )}
          </AsyncBoundary>
        )}
      </div>
    </div>
  );
}

/** One topic: its name and the guides filed under it. */
function CategoryPanel({
  examCode,
  categorySlug,
  title,
  description,
  onOpenArticle,
}: {
  examCode?: string;
  categorySlug: string;
  title?: string;
  description?: string;
  onOpenArticle: (slug: string) => void;
}) {
  const topic = useAsync(async () => {
    const [categories, articles] = await Promise.all([
      fetchHelpCategories(examCode),
      fetchHelpArticles(examCode, categorySlug),
    ]);
    return {
      category: categories.find((candidate) => candidate.slug === categorySlug) ?? null,
      articles,
    };
  }, [examCode, categorySlug]);

  const category: HelpCategory | null = topic.data?.category ?? null;
  const heading = title || category?.title || "Articles";
  const sub = description || category?.description || "";
  const Icon = helpCategoryIcon(category?.icon_key ?? "book");

  return (
    <div className="w-full pb-2">
      <h3 className={helpType.title}>
        {heading}
      </h3>
      {sub ? (
        <p className={`mt-0.5 ${helpType.support}`}>{sub}</p>
      ) : null}

      <div className="mt-4">
        <AsyncBoundary
          state={topic}
          loading={<p className="py-8 text-osce-body text-osce-ink-500">Loading articles…</p>}
        >
          {({ articles }) =>
            articles.length === 0 ? (
              <p className="mt-2 text-osce-body text-osce-ink-500">No articles in this topic.</p>
            ) : (
              <B2CPanelCard>
                <B2CPanelCardHeader>
                  {/* `Icon` is looked up from helpCategoryIcon, not defined here. */}
                  {/* eslint-disable-next-line react-hooks/static-components */}
                  <Icon className="h-4 w-4 text-osce-accent" aria-hidden />
                  Articles
                </B2CPanelCardHeader>
                <ArticleRows articles={articles} onOpenArticle={onOpenArticle} />
              </B2CPanelCard>
            )
          }
        </AsyncBoundary>
      </div>
    </div>
  );
}

/** One guide, with links to the guides related to it. */
function ArticlePanel({
  examCode,
  slug,
  onOpenArticle,
}: {
  examCode?: string;
  slug: string;
  onOpenArticle: (slug: string) => void;
}) {
  const guide = useAsync(async () => {
    const article = await fetchHelpArticle(slug, examCode);
    // A related guide that cannot be read still gets a link, named from its slug.
    const titles = await Promise.all(
      (article.related_slugs ?? []).map(async (relatedSlug) => {
        try {
          return [relatedSlug, (await fetchHelpArticle(relatedSlug, examCode)).title] as const;
        } catch {
          return [relatedSlug, readableSlug(relatedSlug)] as const;
        }
      }),
    );
    const relatedTitles: Record<string, string> = Object.fromEntries(titles);
    return { article, relatedTitles };
  }, [examCode, slug]);

  return (
    <AsyncBoundary
      state={guide}
      loading={<p className="py-8 text-osce-body text-osce-ink-500">Loading…</p>}
    >
      {({ article, relatedTitles }) => (
        <div className="w-full pb-2">
          <h3 className={helpType.title}>
            {article.title}
          </h3>
          <div className="mt-3">
            <MarkdownRenderer
              content={article.body_md}
              className={mdStyles.helpCompact}
            />
          </div>
          {article.related_slugs?.length ? (
            <div className="mt-7 border-t border-osce-border-light pt-5">
              <p className={helpType.title}>
                Related
              </p>
              <ul className="mt-2.5 space-y-2">
                {article.related_slugs.map((relatedSlug) => (
                  <li key={relatedSlug}>
                    <button
                      type="button"
                      onClick={() => onOpenArticle(relatedSlug)}
                      className={`text-left ${helpType.link}`}
                    >
                      {relatedTitles[relatedSlug] || readableSlug(relatedSlug)}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )}
    </AsyncBoundary>
  );
}
