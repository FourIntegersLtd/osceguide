"use client";

import { HiOutlineChevronRight } from "react-icons/hi2";
import React, { useEffect, useState } from "react";
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
  type HelpArticleDetail,
  type HelpArticleListItem,
  type HelpCategory,
} from "@/capabilities/help/api";
import {
  B2CPanelCard,
  B2CPanelCardHeader,
} from "@/foundation/ui/B2CPanelCard";

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

function apiErrorMessage(error: unknown, fallback: string): string {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    "data" in error.response
  ) {
    const data = (
      error.response as { data?: { error?: string; message?: string } }
    ).data;
    if (data?.error) return data.error;
    if (data?.message) return data.message;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

/** `initialArticle` opens straight on one article, as when Athena suggests it. */
export default function HelpArticleBrowse({
  appType,
  initialArticle,
}: {
  appType: string;
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
          appType={appType}
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
          appType={appType}
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
          appType={appType}
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

function BrowsePanel({
  appType,
  onOpenCategory,
  onOpenArticle,
}: {
  appType: string;
  onOpenCategory: (slug: string, title: string, description: string) => void;
  onOpenArticle: (slug: string) => void;
}) {
  const [categories, setCategories] = useState<HelpCategory[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  // What the server is asked for: the box, once typing pauses.
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<HelpArticleListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(searchQuery.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void fetchHelpCategories(appType)
      .then((cats) => {
        if (!cancelled) setCategories(cats);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(apiErrorMessage(e, "Could not load help topics."));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [appType]);

  // The match is the server's: title, summary and category, searched in SQL
  // rather than by holding every article and filtering it in the browser.
  useEffect(() => {
    if (query.length === 0) {
      setSearchResults([]);
      return;
    }
    let cancelled = false;
    setSearching(true);
    void fetchHelpArticles(appType, undefined, query)
      .then((articles) => {
        if (!cancelled) setSearchResults(articles);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(apiErrorMessage(e, "Could not search help topics."));
      })
      .finally(() => {
        if (!cancelled) setSearching(false);
      });
    return () => {
      cancelled = true;
    };
  }, [appType, query]);

  const normalizedQuery = query;

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
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search guides, e.g. Create Session"
          className="w-full rounded-xl border border-osce-border py-2.5 pl-9 pr-3 text-osce-body text-osce-ink-900 outline-none placeholder:text-osce-ink-400 focus:border-osce-accent-light focus:ring-2 focus:ring-osce-accent-muted"
        />
      </label>

      {loading ? (
        <p className="mt-6 py-8 text-osce-body text-osce-ink-500">Loading topics…</p>
      ) : error ? (
        <p className="mt-6 py-4 text-osce-body text-osce-danger">{error}</p>
      ) : normalizedQuery.length > 0 ? (
        <B2CPanelCard className="mt-4">
          <B2CPanelCardHeader>
            {searching
              ? "Searching…"
              : searchResults.length > 0
                ? `${searchResults.length} result${searchResults.length === 1 ? "" : "s"}`
                : "No results"}
          </B2CPanelCardHeader>
          {searching ? null : searchResults.length === 0 ? (
            <p className={`px-4 py-4 ${helpType.support}`}>
              Try different words or browse categories below.
            </p>
          ) : (
            <ul>
              {searchResults.map((article) => (
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
                      <span className={`block ${helpType.rowTitle}`}>
                        {article.title}
                      </span>
                      {article.summary ? (
                        <span className={`mt-0.5 block ${helpType.support}`}>
                          {article.summary}
                        </span>
                      ) : null}
                      {article.category_title ? (
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
          )}
        </B2CPanelCard>
      ) : null}

      {!loading && !error && normalizedQuery.length === 0 ? (
        <B2CPanelCard className="mt-4">
          <B2CPanelCardHeader>Documentation</B2CPanelCardHeader>
          {categories.length === 0 ? (
            <p className="px-4 py-4 text-osce-body text-osce-ink-500">No help topics yet.</p>
          ) : (
            <ul>
              {categories.map((cat) => {
                const Icon = helpCategoryIcon(cat.icon_key);
                return (
                  <li
                    key={cat.id || cat.slug}
                    className="border-b border-osce-border-light last:border-b-0"
                  >
                    <button
                      type="button"
                      onClick={() =>
                        onOpenCategory(cat.slug, cat.title, cat.description)
                      }
                      className="flex w-full items-start gap-3 px-4 py-3.5 text-left transition hover:bg-b2c-surface-muted"
                    >
                      <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-osce-accent-muted text-osce-accent">
                        <Icon className="h-4 w-4" aria-hidden />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className={`block ${helpType.rowTitle}`}>
                          {cat.title}
                        </span>
                        <span className={`mt-0.5 block ${helpType.support}`}>
                          {cat.description}
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
      ) : null}
    </div>
  );
}

function CategoryPanel({
  appType,
  categorySlug,
  title,
  description,
  onOpenArticle,
}: {
  appType: string;
  categorySlug: string;
  title?: string;
  description?: string;
  onOpenArticle: (slug: string) => void;
}) {
  const [category, setCategory] = useState<HelpCategory | null>(null);
  const [articles, setArticles] = useState<HelpArticleListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void Promise.all([
      fetchHelpCategories(appType),
      fetchHelpArticles(appType, categorySlug),
    ])
      .then(([cats, rows]) => {
        if (cancelled) return;
        setCategory(cats.find((c) => c.slug === categorySlug) ?? null);
        setArticles(rows);
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(apiErrorMessage(e, "Could not load articles."));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [appType, categorySlug]);

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

      {loading ? (
        <p className="mt-6 py-8 text-osce-body text-osce-ink-500">Loading articles…</p>
      ) : error ? (
        <p className="mt-6 text-osce-body text-osce-danger">{error}</p>
      ) : articles.length === 0 ? (
        <p className="mt-6 text-osce-body text-osce-ink-500">No articles in this topic.</p>
      ) : (
        <B2CPanelCard className="mt-4">
          <B2CPanelCardHeader>
            {/* `Icon` is looked up from helpCategoryIcon, not defined here. */}
            {/* eslint-disable-next-line react-hooks/static-components */}
            <Icon className="h-4 w-4 text-osce-accent" aria-hidden />
            Articles
          </B2CPanelCardHeader>
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
                    <span className={`block ${helpType.rowTitle}`}>
                      {article.title}
                    </span>
                    {article.summary ? (
                      <span className={`mt-0.5 block ${helpType.support}`}>
                        {article.summary}
                      </span>
                    ) : null}
                  </span>
                  <HiOutlineChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-osce-ink-400" />
                </button>
              </li>
            ))}
          </ul>
        </B2CPanelCard>
      )}
    </div>
  );
}

function ArticlePanel({
  appType,
  slug,
  onOpenArticle,
}: {
  appType: string;
  slug: string;
  onOpenArticle: (slug: string) => void;
}) {
  const [article, setArticle] = useState<HelpArticleDetail | null>(null);
  const [relatedTitles, setRelatedTitles] = useState<Record<string, string>>(
    {},
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setArticle(null);
    setRelatedTitles({});
    void fetchHelpArticle(slug, appType)
      .then(async (row) => {
        if (cancelled) return;
        setArticle(row);
        const related = row.related_slugs ?? [];
        if (related.length === 0) return;
        const pairs = await Promise.all(
          related.map(async (relatedSlug) => {
            try {
              const detail = await fetchHelpArticle(relatedSlug, appType);
              return [relatedSlug, detail.title] as const;
            } catch {
              return [
                relatedSlug,
                relatedSlug.replace(/-/g, " "),
              ] as const;
            }
          }),
        );
        if (!cancelled) {
          setRelatedTitles(Object.fromEntries(pairs));
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(apiErrorMessage(e, "Could not load article."));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [appType, slug]);

  if (loading) {
    return <p className="py-8 text-osce-body text-osce-ink-500">Loading…</p>;
  }
  if (error || !article) {
    return (
      <p className="text-osce-body text-osce-danger">{error ?? "Article not found."}</p>
    );
  }

  return (
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
                  {relatedTitles[relatedSlug] ||
                    relatedSlug.replace(/-/g, " ")}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
