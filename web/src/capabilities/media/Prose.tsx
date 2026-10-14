"use client";

import { MarkdownRenderer, cn } from "@/foundation/ui";

/**
 * Markdown, with its lists visible.
 *
 * `markdown.module.css` sets a list's spacing and padding but never its
 * marker, and Tailwind's preflight removes the browser's — so an ordered list
 * in a summary rendered as three unnumbered lines. The retiring client papered
 * over it with `prose prose-lg` from the typography plugin, which this app
 * does not load. Restoring the two markers is cheaper than the plugin, and
 * keeps every reader in this capability rendering the same.
 *
 * `html` is the same markdown already rendered and sanitised on the server
 * (`renderMarkdownToSafeHtml`), so the first paint has the text a crawler needs.
 */
export function Prose({ content, html, className = "" }: { content: string; html?: string; className?: string }) {
  return (
    <MarkdownRenderer
      content={content}
      html={html}
      className={cn("[&_ol]:list-decimal [&_ul]:list-disc", className)}
    />
  );
}
