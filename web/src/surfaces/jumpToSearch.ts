import { fetchHelpArticles, type HelpArticle } from "@/capabilities/help/api";
import { browseLibrary, type LibraryStation } from "@/capabilities/stations/api";

/** Rows per group: the palette is a shortcut, the library and Help are the full lists. */
const GROUP_SIZE = 5;
/** Wait for a pause in typing before asking the api. */
export const SEARCH_DEBOUNCE_MS = 250;
/** Shorter than this matches too much to be worth a request. */
export const MIN_QUERY_CHARS = 2;

export interface JumpToScope {
  examCode: string | null;
  /** The consumer library is the only one this palette searches; an institution's is per organisation. */
  stations: boolean;
}

export interface JumpToRemote {
  stations: LibraryStation[];
  articles: HelpArticle[];
  /** A group that failed to load is said so, never shown as "no results". */
  failed: boolean;
}

export const NO_REMOTE: JumpToRemote = { stations: [], articles: [], failed: false };

/** What the query finds beyond the nav: library stations and Help articles, each failing alone. */
export async function searchJumpTo(
  query: string,
  scope: JumpToScope,
  signal?: AbortSignal,
  deps: { browseLibrary: typeof browseLibrary; fetchHelpArticles: typeof fetchHelpArticles } = {
    browseLibrary,
    fetchHelpArticles,
  },
): Promise<JumpToRemote> {
  const text = query.trim();
  if (text.length < MIN_QUERY_CHARS) return NO_REMOTE;
  const exam = scope.examCode ?? undefined;
  const [stations, articles] = await Promise.allSettled([
    scope.stations
      ? deps.browseLibrary({ examCode: scope.examCode, search: text, limit: GROUP_SIZE }, signal)
      : Promise.resolve(null),
    deps.fetchHelpArticles(exam, undefined, text),
  ]);
  if (signal?.aborted) return NO_REMOTE;
  return {
    stations: stations.status === "fulfilled" ? stations.value?.items ?? [] : [],
    articles: articles.status === "fulfilled" ? articles.value.slice(0, GROUP_SIZE) : [],
    failed: stations.status === "rejected" || articles.status === "rejected",
  };
}
