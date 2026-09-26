import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "OSCE Guide - Master your Clinical Simulation Exams",
    short_name: "OSCE Guide",
    description: "Master your Clinical Simulation Exams with confidence",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#2563eb",
    orientation: "portrait-primary",
    scope: "/",
    icons: [
      {
        src: "/images/logo/web_app_192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/images/logo/web_app_512.png",
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
