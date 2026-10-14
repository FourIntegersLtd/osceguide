import { ArticleView } from "@/capabilities/media/ArticleView";
import type { MediaItem } from "@/capabilities/media/api";

/** One public article, read and rendered on the server by `/blogs/[slug]`. */
export function BlogArticle({ item, bodyHtml }: { item: MediaItem; bodyHtml: string }) {
  return (
    <main className="mx-auto w-full px-4 py-12 sm:px-6">
      <ArticleView item={item} bodyHtml={bodyHtml} />
    </main>
  );
}
