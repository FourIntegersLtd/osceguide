import { defineConfig, globalIgnores } from "eslint/config";
import next from "eslint-config-next";
import boundaries from "eslint-plugin-boundaries";
import jsxA11y from "eslint-plugin-jsx-a11y";
import tseslint from "typescript-eslint";

/**
 * The tiers of `docs/adr/0001-one-app-shared-capabilities-three-surfaces.md`,
 * enforced rather than documented.
 *
 * The rule that carries the product requirement is the one on `capabilities`:
 * a capability may not import a surface or a domain. That is what keeps help,
 * slides and summaries mountable by institutions later without a port — the
 * moment one of them reads institution or consumer code, it stops being
 * mountable anywhere else, and this is where that is caught.
 */
export default defineConfig([
  globalIgnores([".next/**", ".next-*/**", ".verify/**", "test-results/**", "playwright-report/**", "out/**", "public/mediapipe/**", "next-env.d.ts"]),
  ...next,
  ...tseslint.configs.recommended,
  {
    /**
     * Accessibility (E-15). `eslint-config-next` registers the jsx-a11y plugin
     * but switches on six of its rules; this is the plugin's recommended set,
     * as errors, so a missing label or a click handler on a <div> fails CI the
     * way a tier violation does. It is a floor, not an audit: lint cannot see
     * contrast, focus order or what a screen reader actually announces.
     */
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      ...jsxA11y.flatConfigs.recommended.rules,
      // Our own inputs count as controls, and a label's text often sits a few
      // elements deep (an icon, a span, then the words).
      "jsx-a11y/label-has-associated-control": [
        "error",
        { assert: "either", controlComponents: ["Input", "Select", "Textarea", "AuthoringExamSelect"], depth: 4 },
      ],
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: { boundaries },
    settings: {
      "boundaries/include": ["src/**/*.{ts,tsx}"],
      "boundaries/elements": [
        { type: "app", pattern: "src/app/**" },
        { type: "middleware", pattern: "src/middleware.ts" },
        { type: "surface", pattern: "src/surfaces/**" },
        { type: "domain", mode: "full", pattern: "src/domains/*/**", capture: ["arm"] },
        { type: "capability", mode: "full", pattern: "src/capabilities/*/**", capture: ["name"] },
        { type: "capability-root", pattern: "src/capabilities/*.{ts,tsx}" },
        { type: "foundation", mode: "full", pattern: "src/foundation/*/**", capture: ["module"] },
      ],
    },
    rules: {
      "boundaries/no-unknown-files": "off",
      "boundaries/element-types": [
        "error",
        {
          default: "disallow",
          message: "${file.type} may not import ${dependency.type} — see docs/adr/0001.",
          rules: [
            // Routes compose everything. They hold no logic of their own.
            {
              from: ["app"],
              allow: ["surface", "domain", "capability", "capability-root", "foundation"],
            },
            // A shell mounts domains and capabilities.
            {
              from: ["surface"],
              allow: ["domain", "capability", "capability-root", "foundation"],
            },
            // Middleware answers retiring URLs, so it reads the redirect table
            // and nothing else.
            { from: ["middleware"], allow: ["foundation"] },
            // An arm may use capabilities and the foundation, and itself.
            {
              from: ["domain"],
              allow: [
                ["domain", { arm: "${from.arm}" }],
                "capability",
                "capability-root",
                "foundation",
              ],
            },
            /*
             * No arm reaches into another. Hire used to need an exception
             * here — it is the Assess screens with different wording — and it
             * no longer does: Hire is a *manifest* that declares
             * `screensFrom: "assess"`, resolved in `surfaces/screens.ts`,
             * which is a tier that is allowed to see both. An exception that
             * is no longer needed is one fewer place for a real leak to hide.
             */
            // The rule that matters: capabilities know nothing about arms.
            {
              from: ["capability", "capability-root"],
              allow: ["capability", "capability-root", "foundation"],
              message:
                "A capability may not import a ${dependency.type}. Capabilities mount on any surface; reaching into an arm is what made the help section consumer-only. Take what you need through props or the surface context.",
            },
            // The floor.
            { from: ["foundation"], allow: ["foundation"] },
          ],
        },
      ],
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
      "@typescript-eslint/no-explicit-any": "error",
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "@/foundation/platform-client",
              /*
               * The request function itself, not the whole module: a sign-in
               * page calling `login` and a screen reading `hasCode` off an
               * error are both fine. What is not fine is a component issuing
               * its own request, which is how the retiring consumer client
               * ended up with seventy components calling axios inline, each
               * with its own loading and error handling, none testable.
               */
              importNames: ["platformRequest", "setPlatformTokenSource"],
              message:
                "Requests belong in an api.ts, not in a component. Export a named function from your tier's api.ts and call that.",
            },
          ],
        },
      ],
      /*
       * In-app links are built with `hrefFor` from the surface context, never
       * spelled out. A literal `/app/...` in a component is a link that points
       * at whichever workspace the author happened to be thinking about; ADR
       * 0002 exists because those accumulated.
       */
      "no-restricted-syntax": [
        "error",
        {
          selector: "Literal[value=/^\\/(app|b2b|assess|hire|platform)\\//]",
          message:
            "Do not spell a route prefix. Use `hrefFor()` from the surface context, or `foundation/routing` if this really is about the route space.",
        },
        /*
         * Failures that are swallowed into an empty answer (REGRESSION-PLAN 1.3). A request that
         * fails and renders "nothing here" is a bug nobody sees: the screen must show the failed
         * state, or the catch must say in a comment why the failure is harmless and disable this.
         */
        {
          selector:
            "CallExpression[callee.property.name='catch'][arguments.0.type='ArrowFunctionExpression'][arguments.0.body.type='Literal'][arguments.0.body.value=null]",
          message: "`.catch(() => null)` hides a failed request as an empty result. Show the failed state, or justify and disable.",
        },
        {
          selector:
            "CallExpression[callee.property.name='catch'][arguments.0.type='ArrowFunctionExpression'][arguments.0.body.type='ArrayExpression'][arguments.0.body.elements.length=0]",
          message: "`.catch(() => [])` hides a failed request as an empty list. Show the failed state, or justify and disable.",
        },
        {
          selector:
            "JSXAttribute[name.name='failure'] > JSXExpressionContainer > ArrowFunctionExpression[body.type='Literal'][body.value=null]",
          message: "`failure={() => null}` renders nothing when the request fails. Render the failed state, or justify and disable.",
        },
      ],
      "max-lines": ["warn", { max: 300, skipBlankLines: true, skipComments: true }],
      /*
       * The React Compiler would rather data came from a data layer than an
       * effect, and it is right about product code — which is why every screen
       * here goes through `useAsync` instead of writing its own effect.
       *
       * These three hooks are the exception the rule's own guidance describes:
       * synchronising with an external system (a fetch, an interval, the
       * microphone permission) and calling setState from its callback. Left as
       * warnings so a new violation in product code is still visible, rather
       * than switched off.
       */
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/refs": "warn",
    },
  },
  {
    /*
     * Where talking to the backend is the job.
     *
     * An `api.ts` exists precisely to be the one place a tier makes requests,
     * and `foundation` is the client itself plus the hooks that drive it. The
     * rule is about *components* reaching past them.
     */
    files: [
      "src/**/api.ts",
      "src/**/api/**/*.ts",
      "src/foundation/**/*.{ts,tsx}",
      "src/domains/marketing/support/*.ts",
    ],
    rules: { "no-restricted-imports": "off" },
  },
  {
    /*
     * Where the route space is the subject.
     *
     * `foundation/routing` owns the grammar in ADR 0002 and has to name it;
     * the marketing pages link to public addresses that are not workspace
     * paths at all; and a test asserting a redirect must be able to write the
     * path it is asserting.
     */
    files: [
      "src/foundation/routing/**/*.ts",
      "src/middleware.ts",
      "src/**/*.test.ts",
      "src/domains/marketing/**/*.{ts,tsx}",
    ],
    rules: { "no-restricted-syntax": "off" },
  },
  {
    // Generated from the backend's OpenAPI document. Never edited by hand.
    files: ["src/foundation/platform-client/schema.d.ts"],
    rules: { "max-lines": "off" },
  },
  {
    // Route files are composition, and the barrels are lists.
    files: ["src/app/**/{page,layout,route,template,error,loading,not-found}.tsx", "src/**/index.ts"],
    rules: { "max-lines": "off" },
  },
]);
