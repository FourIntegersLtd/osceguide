import { ArticleView } from "@/capabilities/media/ArticleView";
import type { MediaItem } from "@/capabilities/media/api";

/** One public article, read and rendered on the server by `/blogs/[slug]`. */
export function BlogArticle({ item, bodyHtml }: { item: MediaItem; bodyHtml: string }) {
  return (
    <div className="mx-auto w-full max-w-[1200px] px-4 py-12 sm:px-6 sm:py-16">
      <ArticleView item={item} bodyHtml={bodyHtml} />
    </div>
  );
}
