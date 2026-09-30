/**
 * Canonical B2C design-system hex values (ink + brand blue-600 + feedback bands).
 * Keep in sync with `html:has([data-b2c-shell])` in globals.css and brandTokens.
 */
export const b2cDesignTokens = {
  ink: {
    900: "#101828",
    800: "#1d2939",
    700: "#344054",
    500: "#667085",
    400: "#98a2b3",
    300: "#8a94a6",
  },
  accent: {
    DEFAULT: "#2563eb",
    hover: "#1d4ed8",
    muted: "#eff6ff",
    subtle: "#dbeafe",
  },
  surface: {
    canvas: "#f7f8fa",
    card: "#ffffff",
    inset: "#fcfcfd",
    navActive: "#f2f4f7",
  },
  border: {
    DEFAULT: "#e4e7ec",
    light: "#f2f4f7",
  },
  band: {
    competent: "#22c55e",
    competentBg: "#dcfce7",
    competentBorder: "#86efac",
    developing: "#f59e0b",
    developingBg: "#fef3c7",
    developingBorder: "#fcd34d",
    development: "#ef4444",
    developmentBg: "#fee2e2",
    developmentBorder: "#fca5a5",
  },
  trendBar: {
    empty: "#e4e7ec",
    mid: "#dbeafe",
    active: "#2563eb",
  },
} as const;
