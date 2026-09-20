import type { Config } from "tailwindcss";
import path from "node:path";
import { fileURLToPath } from "node:url";

const platformRoot = path.dirname(fileURLToPath(import.meta.url));
const b2bContent = path.join(platformRoot, "../frontend/src/b2b/**/*.{ts,tsx}");
const sharedContent = path.join(
  platformRoot,
  "../frontend/src/shared/**/*.{ts,tsx}",
);

/**
 * Two palettes, on purpose.
 *
 * `canvas`, `ink`, `accent` and friends are the *semantic* set: they resolve
 * to CSS custom properties that each surface shell overrides, so a component
 * written against them looks right on every arm and a component that writes
 * `bg-blue-600` has picked a side. They live in
 * `src/foundation/ui/tokens.css`.
 *
 * `osce-*`, `b2c-*`, `b2b-*` and `landing-*` are the product's actual colours,
 * brought across from the retiring client with the screens that name them.
 * They are defined in `src/foundation/ui/osceTokens.css`. Ported code keeps
 * using them; new code should reach for the semantic set.
 */
const config: Config = {
  content: [
    "./src/**/*.{ts,tsx}",
    // The `@/b2b` and `@/shared` aliases resolve into the retiring client.
    // Anything imported from there is rendered here, so its classes must be
    // scanned here too, or a `w-[248px]` on a shared component silently
    // never exists in this app's CSS.
    // Dev perf: this widens Tailwind's scan (~500 files). Drop these globs
    // once authoring no longer imports from `frontend/src/b2b` (use a safelist
    // for any remaining arbitrary utilities).
    b2bContent,
    sharedContent,
  ],
  theme: {
    extend: {
      colors: {
        /* The semantic set: overridden per surface. */
        canvas: "rgb(var(--color-canvas) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        "surface-raised": "rgb(var(--color-surface-raised) / <alpha-value>)",
        border: "rgb(var(--color-border) / <alpha-value>)",
        "border-strong": "rgb(var(--color-border) / <alpha-value>)",
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        "ink-muted": "rgb(var(--color-ink-muted) / <alpha-value>)",
        "ink-subtle": "rgb(var(--color-ink-subtle) / <alpha-value>)",
        "ink-inverse": "rgb(var(--color-ink-inverse) / <alpha-value>)",
        accent: "rgb(var(--color-accent) / <alpha-value>)",
        "accent-hover": "rgb(var(--color-accent-hover) / <alpha-value>)",
        "accent-subtle": "rgb(var(--color-accent-subtle) / <alpha-value>)",
        danger: "rgb(var(--color-danger) / <alpha-value>)",
        "danger-subtle": "rgb(var(--color-danger-subtle) / <alpha-value>)",
        success: "rgb(var(--color-success) / <alpha-value>)",
        "success-subtle": "rgb(var(--color-success-subtle) / <alpha-value>)",
        warning: "rgb(var(--color-warning) / <alpha-value>)",
        "warning-subtle": "rgb(var(--color-warning-subtle) / <alpha-value>)",

        /* The product palette, from the retiring client. */
        background: "var(--background)",
        foreground: "var(--foreground)",
        /**
         * Canonical OSCE Guide palette. `b2c-*`, `b2b-*` and `landing-*`
         * below are being migrated onto these; prefer `osce-*` in new code.
         */
        osce: {
          canvas: "var(--osce-canvas)",
          surface: {
            DEFAULT: "var(--osce-surface)",
            inset: "var(--osce-surface-inset)",
          },
          navActive: "var(--osce-nav-active)",
          border: {
            DEFAULT: "var(--osce-border)",
            light: "var(--osce-border-light)",
          },
          ink: {
            900: "var(--osce-ink-900)",
            800: "var(--osce-ink-800)",
            700: "var(--osce-ink-700)",
            600: "var(--osce-ink-600)",
            500: "var(--osce-ink-500)",
            400: "var(--osce-ink-400)",
          },
          accent: {
            DEFAULT: "var(--osce-accent)",
            hover: "var(--osce-accent-hover)",
            muted: "var(--osce-accent-muted)",
            subtle: "var(--osce-accent-subtle)",
            light: "var(--osce-accent-light)",
          },
          success: {
            solid: "var(--osce-success-solid)",
            solidHover: "var(--osce-success-solid-hover)",
            bg: "var(--osce-success-bg)",
            border: "var(--osce-success-border)",
            text: "var(--osce-success-text)",
            icon: "var(--osce-success-icon)",
          },
          warning: {
            bg: "var(--osce-warning-bg)",
            border: "var(--osce-warning-border)",
            text: "var(--osce-warning-text)",
            icon: "var(--osce-warning-icon)",
          },
          danger: {
            DEFAULT: "var(--osce-danger)",
            hover: "var(--osce-danger-hover)",
            bg: "var(--osce-danger-bg)",
            border: "var(--osce-danger-border)",
            text: "var(--osce-danger-text)",
            icon: "var(--osce-danger-icon)",
          },
          info: {
            bg: "var(--osce-info-bg)",
            border: "var(--osce-info-border)",
            text: "var(--osce-info-text)",
            icon: "var(--osce-info-icon)",
          },
          /** Reading tones — colour by stage of the consultation. */
          tone: {
            history: {
              bg: "var(--osce-tone-history-bg)",
              header: "var(--osce-tone-history-header)",
              border: "var(--osce-tone-history-border)",
              text: "var(--osce-tone-history-text)",
              body: "var(--osce-tone-history-body)",
            },
            examination: {
              bg: "var(--osce-tone-examination-bg)",
              header: "var(--osce-tone-examination-header)",
              border: "var(--osce-tone-examination-border)",
              text: "var(--osce-tone-examination-text)",
              body: "var(--osce-tone-examination-body)",
            },
            reasoning: {
              bg: "var(--osce-tone-reasoning-bg)",
              header: "var(--osce-tone-reasoning-header)",
              border: "var(--osce-tone-reasoning-border)",
              text: "var(--osce-tone-reasoning-text)",
              body: "var(--osce-tone-reasoning-body)",
            },
            management: {
              bg: "var(--osce-tone-management-bg)",
              header: "var(--osce-tone-management-header)",
              border: "var(--osce-tone-management-border)",
              text: "var(--osce-tone-management-text)",
              body: "var(--osce-tone-management-body)",
            },
            safety: {
              bg: "var(--osce-tone-safety-bg)",
              header: "var(--osce-tone-safety-header)",
              border: "var(--osce-tone-safety-border)",
              text: "var(--osce-tone-safety-text)",
              body: "var(--osce-tone-safety-body)",
            },
            education: {
              bg: "var(--osce-tone-education-bg)",
              header: "var(--osce-tone-education-header)",
              border: "var(--osce-tone-education-border)",
              text: "var(--osce-tone-education-text)",
              body: "var(--osce-tone-education-body)",
            },
          },
          /** Live session video chrome — the product's only dark surface. */
          video: {
            bg: "var(--osce-video-bg)",
            raised: "var(--osce-video-bg-raised)",
            inactive: "var(--osce-video-inactive)",
            accent: "var(--osce-video-accent)",
            accentRing: "var(--osce-video-accent-ring)",
            accentInk: "var(--osce-video-accent-ink)",
          },
          band: {
            competent: "var(--osce-band-competent)",
            competentBg: "var(--osce-band-competent-bg)",
            competentBorder: "var(--osce-band-competent-border)",
            developing: "var(--osce-band-developing)",
            developingBg: "var(--osce-band-developing-bg)",
            developingBorder: "var(--osce-band-developing-border)",
            development: "var(--osce-band-development)",
            developmentBg: "var(--osce-band-development-bg)",
            developmentBorder: "var(--osce-band-development-border)",
          },
        },
        brand: {
          primary: {
            DEFAULT: "var(--brand-primary)",
            hover: "var(--brand-primary-hover)",
            muted: "var(--brand-primary-muted)",
            subtle: "var(--brand-primary-subtle)",
            light: "var(--brand-primary-light)",
          },
          danger: {
            DEFAULT: "var(--brand-danger)",
            hover: "var(--brand-danger-hover)",
          },
        },
        b2c: {
          primary: {
            DEFAULT: "var(--b2c-primary)",
            hover: "var(--b2c-primary-hover)",
            muted: "var(--b2c-primary-muted)",
            subtle: "var(--b2c-primary-subtle)",
            light: "var(--b2c-primary-light)",
          },
          secondary: {
            DEFAULT: "var(--b2c-secondary)",
            hover: "var(--b2c-secondary-hover)",
          },
          danger: {
            DEFAULT: "var(--b2c-danger)",
            hover: "var(--b2c-danger-hover)",
          },
          surface: {
            DEFAULT: "var(--b2c-surface)",
            muted: "var(--b2c-surface-muted)",
          },
          navActive: "var(--b2c-nav-active)",
          border: {
            DEFAULT: "var(--b2c-border, var(--osce-border))",
            light: "var(--b2c-border-light, var(--osce-border-light))",
          },
          text: {
            primary: "var(--b2c-text-primary)",
            secondary: "var(--b2c-text-secondary)",
            muted: "var(--b2c-text-muted)",
          },
          band: {
            competent: "var(--b2c-band-competent)",
            competentBg: "var(--b2c-band-competent-bg)",
            competentBorder: "var(--b2c-band-competent-border)",
            developing: "var(--b2c-band-developing)",
            developingBg: "var(--b2c-band-developing-bg)",
            developingBorder: "var(--b2c-band-developing-border)",
            development: "var(--b2c-band-development)",
            developmentBg: "var(--b2c-band-development-bg)",
            developmentBorder: "var(--b2c-band-development-border)",
          },
        },
        landing: {
          ink: {
            DEFAULT: "var(--landing-ink)",
            hover: "var(--landing-ink-hover)",
            body: "var(--landing-ink-body)",
            muted: "var(--landing-ink-muted)",
          },
          /**
           * Marketing surface tokens. Fallbacks equal the pre-cream values, so
           * exam landings and B2B marketing render unchanged; the cream canvas
           * is opted into by `[data-b2c-landing-surface="cream"]` in globals.css.
           */
          canvas: "var(--landing-canvas, #ffffff)",
          band: "var(--landing-band, #ffffff)",
          wash: "var(--landing-wash, #ffffff)",
          nav: "var(--landing-nav, rgba(255, 255, 255, 0.86))",
          card: {
            DEFAULT: "var(--landing-card, #ffffff)",
            muted: "var(--landing-card-muted, #fcfcfd)",
            accent: "var(--landing-card-accent, #f3f6fa)",
          },
          warm: {
            DEFAULT: "var(--landing-warm, var(--b2c-border))",
            strong: "var(--landing-warm-strong, #d0d5dd)",
          },
          divider: "var(--landing-divider, #edf0f3)",
          hairline: "var(--landing-hairline, var(--b2c-border-light))",
          price: "var(--landing-price, var(--b2c-text-primary))",
        },
        b2b: {
          canvas: "var(--b2b-canvas)",
          surface: "var(--b2b-surface)",
          cream: "var(--b2b-cream)",
          border: "var(--b2b-border, var(--osce-border))",
          subtle: "var(--b2b-subtle)",
          beige: "var(--b2b-beige)",
          headline: "var(--b2b-headline)",
          body: "var(--b2b-body)",
          graphite: "var(--b2b-graphite)",
          mid: "var(--b2b-mid)",
          footer: "var(--b2b-footer)",
          icon: "var(--b2b-icon)",
          btnMuted: "var(--b2b-btn-muted)",
          placeholder: "var(--b2b-placeholder)",
          inactive: "var(--b2b-inactive)",
          accent: {
            DEFAULT: "var(--b2b-accent)",
            hover: "var(--b2b-accent-hover)",
            bg: "var(--b2b-accent-bg)",
            border: "var(--b2b-accent-border)",
          },
          success: {
            bg: "var(--b2b-success-bg)",
            border: "var(--b2b-success-border)",
            text: "var(--b2b-success-text)",
            icon: "var(--b2b-success-icon)",
          },
          warning: {
            bg: "var(--b2b-warning-bg)",
            border: "var(--b2b-warning-border)",
            text: "var(--b2b-warning-text)",
            icon: "var(--b2b-warning-icon)",
          },
          danger: {
            DEFAULT: "var(--b2b-danger)",
            hover: "var(--b2b-danger-hover)",
            bg: "var(--b2b-danger-bg)",
            border: "var(--b2b-danger-border)",
            text: "var(--b2b-danger-text)",
            icon: "var(--b2b-danger-icon)",
          },
          info: {
            bg: "var(--b2b-info-bg)",
            border: "var(--b2b-info-border)",
            text: "var(--b2b-info-text)",
            icon: "var(--b2b-info-icon)",
          },
          chip: {
            blue: {
              bg: "var(--b2b-chip-blue-bg)",
              text: "var(--b2b-chip-blue-text)",
            },
            violet: {
              bg: "var(--b2b-chip-violet-bg)",
              text: "var(--b2b-chip-violet-text)",
            },
            green: {
              bg: "var(--b2b-chip-green-bg)",
              text: "var(--b2b-chip-green-text)",
            },
            amber: {
              bg: "var(--b2b-chip-amber-bg)",
              text: "var(--b2b-chip-amber-text)",
            },
            rose: {
              bg: "var(--b2b-chip-rose-bg)",
              text: "var(--b2b-chip-rose-text)",
            },
            teal: {
              bg: "var(--b2b-chip-teal-bg)",
              text: "var(--b2b-chip-teal-text)",
            },
          },
        },
      },
      /* Preflight uses this for uncoloured `border` — not currentColor/ink. */
      borderColor: {
        DEFAULT: "rgb(var(--color-border) / <alpha-value>)",
      },
      
      fontSize: {
        /**
         * The type scale. One ramp for the app, the B2B workspace and
         * marketing — the former `b2c-*` and `b2b-*` scales are gone.
         *
         * Headings are fluid: `clamp(min, base + vw, max)`, tuned so each
         * token sits at its minimum by 375px and reaches its maximum at
         * 1024px (`lg`). The former fixed values are preserved as the
         * maxima, so desktop is unchanged — only narrow viewports differ.
         *
         * Because the ramp scales itself, call sites must NOT pair a token
         * with a responsive step-up (`text-osce-title sm:text-osce-heading`).
         * That double-scales. Pick one token and let it breathe.
         *
         * Small UI text is deliberately NOT fluid: captions and data labels
         * are already at the legibility floor and must not shrink further.
         */
        /** Dense overlay chrome only — video tile pills, tight status labels. */
        "osce-micro": ["10px", { lineHeight: "1.3" }],
        "osce-caption": ["11px", { lineHeight: "1.4" }],
        "osce-meta": ["13px", { lineHeight: "1.5" }],
        "osce-data": ["14px", { lineHeight: "1.5" }],
        /**
         * 16px, not 15px. Inputs render at this size, and iOS Safari zooms
         * the viewport whenever a focused field is under 16px. The zoom is
         * not reversible by the user and leaves the layout offset, so the
         * floor is a functional requirement rather than a taste call.
         */
        "osce-body": ["16px", { lineHeight: "1.5" }],
        "osce-subheading": [
          "clamp(1.0625rem, 0.99rem + 0.308vw, 1.1875rem)",
          { lineHeight: "1.4", letterSpacing: "-0.02em" },
        ],
        "osce-title": [
          "clamp(1.1875rem, 1.043rem + 0.616vw, 1.4375rem)",
          { lineHeight: "1.25", letterSpacing: "-0.02em" },
        ],
        "osce-heading": [
          "clamp(1.3125rem, 1.096rem + 0.925vw, 1.6875rem)",
          { lineHeight: "1.25", letterSpacing: "-0.02em" },
        ],
        "osce-display-sm": [
          "clamp(1.625rem, 1.3rem + 1.387vw, 2.1875rem)",
          { lineHeight: "1.15", letterSpacing: "-0.02em" },
        ],
        "osce-display": [
          "clamp(2rem, 1.458rem + 2.311vw, 2.9375rem)",
          { lineHeight: "1.1", letterSpacing: "-0.02em" },
        ],
        "osce-display-lg": [
          "clamp(2.25rem, 1.419rem + 3.544vw, 3.6875rem)",
          { lineHeight: "1.05", letterSpacing: "-0.02em" },
        ],
      },
      maxWidth: {
        /** Page + landing section cap. One width for every surface. */
        "osce-page": "1200px",
        /** Marketing copy and narrow prose columns. */
        "osce-narrow": "820px",
        /** Long-form reading measure. */
        "osce-prose": "68ch",
      },
      borderRadius: {
        /* The semantic pair the new primitives use. */
        control: "var(--radius-control)",
        panel: "var(--radius-panel)",
        "osce-sm": "var(--osce-radius-sm)",
        "osce-md": "var(--osce-radius-md)",
        "osce-lg": "var(--osce-radius-lg)",
        "osce-xl": "var(--osce-radius-xl)",
        b2b: "8px",
        "b2b-sm": "6px",
        "landing-card": "var(--landing-radius-card, 0.75rem)",
        "landing-cta": "var(--landing-radius-cta, 6px)",
        "landing-panel": "var(--landing-radius-panel, 20px)",
        "landing-panel-sm": "var(--landing-radius-panel-sm, 28px)",
        "landing-panel-lg": "var(--landing-radius-panel-lg, 32px)",
      },
      boxShadow: {
        "landing-card": "var(--landing-shadow-card, 0 0 #0000)",
        "landing-card-hover": "var(--landing-shadow-card-hover, 0 0 #0000)",
        "landing-soft": "var(--landing-shadow-soft, 0 1px 3px rgba(16, 24, 40, 0.06))",
        "landing-panel": "var(--landing-shadow-panel, 0 8px 32px rgba(16, 24, 40, 0.04))",
        "landing-showcase":
          "var(--landing-shadow-showcase, 0 16px 40px rgba(16, 24, 40, 0.1))",
        "landing-showcase-side":
          "var(--landing-shadow-showcase-side, 0 8px 24px rgba(16, 24, 40, 0.06))",
        "landing-cta": "var(--landing-shadow-cta, 0 0 #0000)",
        "landing-cta-secondary":
          "var(--landing-shadow-cta-secondary, 0 1px 2px rgba(16, 24, 40, 0.05))",
      },
      fontFamily: {
        "landing-heading": [
          "var(--font-archivo)",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        "landing-body": [
          "var(--font-inter)",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        "landing-mono": [
          "var(--font-ibm-plex-mono)",
          "ui-monospace",
          "monospace",
        ],
        sans: [
          "var(--font-inter)",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        heading: [
          "var(--font-archivo)",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        archivo: [
          "var(--font-archivo)",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        b2b: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        inter: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
