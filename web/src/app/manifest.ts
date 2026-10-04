import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "OSCE Guide - Master your Clinical Simulation Exams",
    short_name: "OSCE Guide",
    description: "Master your Clinical Simulation Exams with confidence",
    // `id` stays at the old start URL so existing installs are still this app.
    id: "/",
    // Straight to the app (or sign-in), not the marketing landing and its redirect.
    start_url: "/app",
    display: "standalone",
    background_color: "#ffffff",
    // Matches the viewport's theme colour, so the launch does not flash blue.
    theme_color: "#ffffff",
    orientation: "portrait-primary",
    scope: "/",
    icons: [
      {
        src: "/images/logo/web_app_192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/images/logo/web_app_512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      // The only one safe to crop: opaque, with the logo inside the safe zone.
      {
        src: "/images/logo/web_app_maskable_512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
    categories: ["education", "medical", "productivity"],
    lang: "en",
    dir: "ltr",
  };
}
