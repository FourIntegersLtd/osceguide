import assert from "node:assert/strict";
import test from "node:test";

import { escapeHtml, renderMarkdownToSafeHtml } from "@/foundation/ui/renderMarkdown";

// Security regression for finding SEC-002 (stored / model-driven XSS).
//
// MarkdownRenderer renders lower-trust strings — ortho station content authored
// by org staff, help articles, and the AI tutor's own chat replies — through
// `dangerouslySetInnerHTML`. The pipeline runs `rehype-raw` (raw HTML is
// parsed), so before `rehype-sanitize` was added, any `<script>`, `onerror=`
// handler or `javascript:` URL in that content executed in the victim's
// session. These assert the sanitiser strips the dangerous constructs while
// keeping ordinary formatting.

test("a <script> tag is stripped from rendered markdown", async () => {
  const html = await renderMarkdownToSafeHtml("Hello <script>alert(1)</script> world");
  assert.ok(!/<script/i.test(html), `script survived: ${html}`);
  assert.ok(html.includes("Hello"));
});

test("an onerror image handler is stripped", async () => {
  const html = await renderMarkdownToSafeHtml('<img src=x onerror="alert(document.cookie)">');
  assert.ok(!/onerror/i.test(html), `event handler survived: ${html}`);
});

test("a javascript: link is neutralised", async () => {
  const html = await renderMarkdownToSafeHtml("[click](javascript:alert(1))");
  assert.ok(!/javascript:/i.test(html), `javascript: URL survived: ${html}`);
});

test("an iframe is stripped", async () => {
  const html = await renderMarkdownToSafeHtml('<iframe src="https://evil.example"></iframe>');
  assert.ok(!/<iframe/i.test(html), `iframe survived: ${html}`);
});

test("ordinary formatting and safe links still render", async () => {
  const html = await renderMarkdownToSafeHtml("# Title\n\n**bold** and [a link](https://example.com)");
  assert.ok(/<h1/i.test(html), `heading missing: ${html}`);
  assert.ok(/<strong>bold<\/strong>/i.test(html), `bold missing: ${html}`);
  assert.ok(/href="https:\/\/example\.com"/i.test(html), `safe link missing: ${html}`);
});

test("code-block language classes survive sanitising", async () => {
  const html = await renderMarkdownToSafeHtml("```js\nconst a = 1;\n```");
  assert.ok(/language-js/.test(html), `language class stripped: ${html}`);
});

test("escapeHtml neutralises angle brackets and quotes", () => {
  assert.equal(escapeHtml('<b>"x"</b>'), "&lt;b&gt;&quot;x&quot;&lt;/b&gt;");
});
