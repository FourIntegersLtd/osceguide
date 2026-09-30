import { remark } from "remark";
import remarkRehype from "remark-rehype";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import rehypeStringify from "rehype-stringify";

// The sanitiser uses rehype's GitHub-derived default schema: no <script>, no
// event handlers, no javascript: URLs, no <iframe>/<object>, while keeping
// ordinary formatting and code-block `language-*` classes (the default already
// allows `className` on <code>). Every string rendered through this is
// lower-trust — ortho station content authored by org staff, help articles,
// and *the AI tutor's own chat replies* — so an unsanitised
// `dangerouslySetInnerHTML` downstream was a stored-/model-driven-XSS sink.
// If a caller ever needs to widen the schema, pass an explicit one here; never
// re-enable `script`, `style` or `on*`.

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Turn markdown (which may embed raw HTML) into a sanitised HTML string safe to
 * inject with `dangerouslySetInnerHTML`. On any pipeline error it returns the
 * input as escaped text rather than raw HTML, so a failure can never reopen the
 * sink.
 */
export async function renderMarkdownToSafeHtml(content: string): Promise<string> {
  if (!content) return "";
  try {
    const result = await remark()
      .use(remarkRehype, { allowDangerousHtml: true })
      .use(rehypeRaw)
      .use(rehypeSanitize)
      .use(rehypeStringify)
      .process(content);
    return String(result);
  } catch (error) {
    console.error("Error processing markdown:", error);
    return escapeHtml(content);
  }
}
