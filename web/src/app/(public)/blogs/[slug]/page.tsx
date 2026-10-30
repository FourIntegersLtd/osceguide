import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { JsonLd } from "@/app/SiteJsonLd";
import { SITE_URL, publicPageMetadata } from "@/app/metadata";
import type { MediaItem } from "@/capabilities/media/api";
import { BlogArticle } from "@/capabilities/media/BlogArticle";
import { articleBlurb, blogPath } from "@/capabilities/media/blogs";
import { SiteShell } from "@/domains/marketing/site/SiteShell";
import { readBlogPost } from "@/capabilities/media/blogsServer";

// Not `revalidate`: the root layout reads the CSP nonce from the request, so every
// page is rendered per request, and the post is read fresh.

const DESCRIPTION_MAX = 160;

function describe(item: MediaItem): string {
  return articleBlurb(item, DESCRIPTION_MAX) || "An article from the OSCE Guide study team.";
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const post = await readBlogPost(slug);
  if (!post) return {};
  const { item } = post;
  const head = publicPageMetadata({ path: blogPath(slug), title: item.title, description: describe(item) });
  return {
    ...head,
    openGraph: {
      ...head.openGraph,
      type: "article",
      publishedTime: item.published_at ?? undefined,
      modifiedTime: item.updated_at,
    },
  };
}

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = await readBlogPost(slug);
  if (!post) notFound();
  const { item, bodyHtml } = post;
  return (
    <SiteShell>
      <JsonLd
        data={{
          "@context": "https://schema.org",
          "@type": "BlogPosting",
          headline: item.title,
          description: describe(item),
          datePublished: item.published_at ?? undefined,
          dateModified: item.updated_at,
          mainEntityOfPage: `${SITE_URL}${blogPath(slug)}`,
          inLanguage: "en-GB",
          author: { "@id": `${SITE_URL}/#organization` },
          publisher: { "@id": `${SITE_URL}/#organization` },
        }}
      />
      <BlogArticle item={item} bodyHtml={bodyHtml} />
    </SiteShell>
  );
}
