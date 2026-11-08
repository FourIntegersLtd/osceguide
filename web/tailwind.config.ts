import type { Config } from "tailwindcss";
import path from "node:path";
import { fileURLToPath } from "node:url";

const platformRoot = path.dirname(fileURLToPath(import.meta.url));
const b2bContent = path.join(platformRoot, "../frontend/src/b2b/**/*.{ts,tsx}");
const sharedContent = path.join(
  platformRoot,
  "../frontend/src/shared/**/*.{ts,tsx}",
);

type ColourTree = { [name: string]: string | ColourTree };

/**
 * Makes the product palette accept an opacity suffix (`bg-osce-surface/80`,
 * `focus:ring-osce-accent/20`).
 *
 * These colours are whole CSS variables (`var(--osce-accent)`), and Tailwind
 * cannot put an alpha into one: for years a class like `bg-osce-accent-muted/60`
 * generated no CSS at all, so tints, focus rings and translucent overlays
 * across the app were silently missing. With a suffix the colour is now mixed
 * with transparent; without one the output is the plain variable, exactly as
 * before, so nothing that already worked changes.
 */
function alphaReady(tree: ColourTree): ColourTree {
  return Object.fromEntries(
    Object.entries(tree).map(([name, value]) => {
      if (typeof value !== "string") return [name, alphaReady(value)];
      if (!value.startsWith("var(")) return [name, value];
      const colour = ({ opacityValue }: { opacityValue?: string | number }) => {
        const opacity = String(opacityValue ?? "");
        // No suffix: Tailwind passes its own `var(--tw-…-opacity)` here.
        if (opacity === "" || opacity.startsWith("var(")) return value;
        // The transparent end Tailwind derives for a gradient's `from-*`.
        if (Number(opacity) === 0) return "rgb(255 255 255 / 0)";
        return `color-mix(in srgb, ${value} calc(${opacity} * 100%), transparent)`;
      };
      return [name, colour as unknown as string];
    }),
  );
}

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
      colors: alphaReady({
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
          commit: {
            DEFAULT: "var(--osce-commit)",
            hover: "var(--osce-commit-hover)",
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
            competentBar: "var(--osce-band-competent-bar)",
            developing: "var(--osce-band-developing)",
            developingBg: "var(--osce-band-developing-bg)",
            developingBorder: "var(--osce-band-developing-border)",
            developingBar: "var(--osce-band-developing-bar)",
            development: "var(--osce-band-development)",
            developmentBg: "var(--osce-band-development-bg)",
            developmentBorder: "var(--osce-band-development-border)",
            developmentBar: "var(--osce-band-development-bar)",
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
        site: {
          ground: "var(--site-ground)",
          card: "var(--site-card)",
          ink: "var(--site-ink)",
          navy: "var(--site-navy)",
          brand: "var(--site-brand)",
          "brand-hover": "var(--site-brand-hover)",
          "on-brand": "var(--site-on-brand)",
          pale: "var(--site-pale)",
          "pale-strong": "var(--site-pale-strong)",
          body: "var(--site-body)",
          muted: "var(--site-muted)",
          faint: "var(--site-faint)",
          line: "var(--site-line)",
          rule: "var(--site-rule)",
          "on-navy": "var(--site-on-navy)",
          "on-navy-dim": "var(--site-on-navy-dim)",
          amber: "var(--site-amber)",
          "amber-bg": "var(--site-amber-bg)",
        },
        /* The assess boards' own chip tint (tokens.css). */
        assess: {
          "warn-text": "var(--assess-warn-text)",
          "hero-live-bg": "var(--assess-hero-live-bg)",
          "selected-bg": "var(--assess-selected-bg)",
          "chip-info-bg": "var(--assess-chip-info-bg)",
          "chip-info-text": "var(--assess-chip-info-text)",
          /* Outside the assess skin the vars are unset: fall back to the accent as before. */
          "select-border": "var(--assess-select-border, var(--osce-accent))",
          "focus-ring": "var(--assess-focus-ring, var(--osce-accent-subtle))",
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
      }),
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
        /**
         * The assess skin's board scale (docs/institution-overhaul/boards): fixed px, no
         * fluid clamp and no tracking, because the boards are the specification and they
         * draw these literal sizes. Used only through the `assess*` strings in b2bTokens.ts.
         */
        "assess-h1": ["28px", { lineHeight: "1.2", letterSpacing: "0" }],
        "assess-card-title": ["26px", { lineHeight: "1.2", letterSpacing: "0" }],
        "assess-state-title": ["16px", { lineHeight: "normal", letterSpacing: "0" }],
        "assess-hero": ["20px", { lineHeight: "normal", letterSpacing: "0" }],
        "assess-section": ["20px", { lineHeight: "1.3", letterSpacing: "0" }],
        "assess-h2": ["24px", { lineHeight: "1.3", letterSpacing: "0" }],
        "assess-desc": ["16px", { lineHeight: "1.5", letterSpacing: "0" }],
        "assess-meta": ["13px", { lineHeight: "1.5", letterSpacing: "0" }],
        "assess-label": ["14px", { lineHeight: "normal", letterSpacing: "0" }],
        "assess-chip": ["12px", { lineHeight: "normal", letterSpacing: "0" }],
        "assess-eyebrow": ["11px", { lineHeight: "normal", letterSpacing: "0.06em" }],
        "assess-num": ["28px", { lineHeight: "normal", letterSpacing: "0" }],
        /** Dense overlay chrome only — video tile pills, tight status labels. */
        "osce-micro": ["var(--osce-fs-micro, 10px)", { lineHeight: "var(--osce-lh-micro, 1.3)" }],
        "osce-caption": ["var(--osce-fs-caption, 11px)", { lineHeight: "var(--osce-lh-caption, 1.4)" }],
        "osce-meta": ["var(--osce-fs-meta, 13px)", { lineHeight: "var(--osce-lh-meta, 1.5)" }],
        "osce-data": ["var(--osce-fs-data, 14px)", { lineHeight: "var(--osce-lh-data, 1.5)" }],
        /**
         * 16px, not 15px. Inputs render at this size, and iOS Safari zooms
         * the viewport whenever a focused field is under 16px. The zoom is
         * not reversible by the user and leaves the layout offset, so the
         * floor is a functional requirement rather than a taste call.
         */
        "osce-body": ["var(--osce-fs-body, 16px)", { lineHeight: "var(--osce-lh-body, 1.5)" }],
        "osce-subheading": [
          "var(--osce-fs-subheading, clamp(1.0625rem, 0.99rem + 0.308vw, 1.1875rem))",
          { lineHeight: "var(--osce-lh-subheading, 1.4)", letterSpacing: "-0.02em" },
        ],
        "osce-title": [
          "var(--osce-fs-title, clamp(1.1875rem, 1.043rem + 0.616vw, 1.4375rem))",
          { lineHeight: "var(--osce-lh-title, 1.25)", letterSpacing: "-0.02em" },
        ],
        "osce-heading": [
          "var(--osce-fs-heading, clamp(1.3125rem, 1.096rem + 0.925vw, 1.6875rem))",
          { lineHeight: "var(--osce-lh-heading, 1.25)", letterSpacing: "-0.02em" },
        ],
        "osce-display-sm": [
          "var(--osce-fs-display-sm, clamp(1.625rem, 1.3rem + 1.387vw, 2.1875rem))",
          { lineHeight: "var(--osce-lh-display-sm, 1.15)", letterSpacing: "-0.02em" },
        ],
        "osce-display": [
          "var(--osce-fs-display, clamp(2rem, 1.458rem + 2.311vw, 2.9375rem))",
          { lineHeight: "var(--osce-lh-display, 1.1)", letterSpacing: "-0.02em" },
        ],
        "osce-display-lg": [
          "var(--osce-fs-display-lg, clamp(2.25rem, 1.419rem + 3.544vw, 3.6875rem))",
          { lineHeight: "var(--osce-lh-display-lg, 1.05)", letterSpacing: "-0.02em" },
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
      spacing: {
        /** Board control metrics: step dot, button side padding, stat tile padding. */
        "assess-dot": "28px",
        "assess-btn": "18px",
        "assess-stat": "18px",
      },
      boxShadow: {
        "board-dialog": "0 20px 60px rgba(0,0,0,0.18)",
        "board-sheet": "0 24px 48px rgba(16,24,40,0.18)",
        "osce-modal": "0 24px 64px rgba(16,24,40,0.18)",
        "home-lift": "0 1px 2px rgba(16,24,40,0.04), 0 12px 32px rgba(16,24,40,0.06)",
        "osce-segmented": "0 1px 2px rgba(0,0,0,0.08), 0 0 0 0.5px rgba(0,0,0,0.04)",
      },
      borderRadius: {
        /* The semantic pair the new primitives use. */
        control: "var(--radius-control)",
        panel: "var(--radius-panel)",
        "osce-sm": "var(--osce-radius-sm)",
        "osce-md": "var(--osce-radius-md)",
        "osce-lg": "var(--osce-radius-lg)",
        "osce-xl": "var(--osce-radius-xl)",
        "osce-2xl": "var(--osce-radius-2xl)",
        /* The boards' own radii: tabs, cards and fields, dialogs, sheets. */
        "board-xs": "5px",
        "board-sm": "7px",
        board: "9px",
        "board-lg": "14px",
        "board-xl": "16px",
        b2b: "8px",
        "b2b-sm": "6px",
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
        /*
         * `--font-ui` / `--font-heading-face` are set by train's skin
         * (tokens.css); unset, the other arms keep Inter and Archivo.
         */
        sans: [
          "var(--font-ui, var(--font-inter))",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        heading: [
          "var(--font-heading-face, var(--font-archivo))",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        /** Page titles only (train): Fraunces, per the canvas. */
        title: ["var(--font-fraunces)", "Georgia", "serif"],
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
