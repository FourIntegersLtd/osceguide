"use client";

import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { readMedia } from "@/capabilities/media/api";
import { ArticleView } from "@/capabilities/media/ArticleView";

/** One public article, by slug. A draft or a different kind is the api's 404. */
export function BlogArticle({ slug }: { slug: string }) {
  const state = useAsync((signal) => readMedia(slug, signal), [slug]);
  return (
    <main className="mx-auto w-full px-4 py-12 sm:px-6">
      <AsyncBoundary state={state}>{(item) => <ArticleView item={item} />}</AsyncBoundary>
    </main>
  );
}
