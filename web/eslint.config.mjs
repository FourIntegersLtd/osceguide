import { defineConfig, globalIgnores } from "eslint/config";
import next from "eslint-config-next";
import boundaries from "eslint-plugin-boundaries";
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
  globalIgnores([".next/**", "out/**", "next-env.d.ts"]),
  ...next,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: { boundaries },
    settings: {
      "boundaries/include": ["src/**/*.{ts,tsx}"],
      "boundaries/elements": [
        { type: "app", pattern: "src/app/**" },
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
            // Hire is a shell over Assess (ADR 0001), so it alone may reach across.
            {
              from: [["domain", { arm: "hire" }]],
              allow: [["domain", { arm: "assess" }]],
            },
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
