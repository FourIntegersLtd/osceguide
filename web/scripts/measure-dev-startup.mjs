#!/usr/bin/env node
/**
 * Rough local dev startup timing (Turbopack or webpack).
 *
 * Usage:
 *   node scripts/measure-dev-startup.mjs
 *   node scripts/measure-dev-startup.mjs --webpack
 *
 * Prints seconds until the dev server responds on :3100. Does not hit a route;
 * use the browser or curl for first-route compile after this.
 */
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const useWebpack = process.argv.includes("--webpack");
const port = 3100;
const url = `http://127.0.0.1:${port}/`;
const root = fileURLToPath(new URL("..", import.meta.url));

const child = spawn(
  useWebpack ? "npm run dev:webpack" : "npm run dev",
  [],
  { cwd: root, stdio: ["ignore", "pipe", "pipe"], shell: true },
);

const started = Date.now();
let readyLogged = false;

child.stdout.on("data", (chunk) => {
  const text = chunk.toString();
  process.stdout.write(text);
  if (!readyLogged && /ready/i.test(text)) {
    readyLogged = true;
    console.error(`\n[measure-dev-startup] "Ready" log at ${((Date.now() - started) / 1000).toFixed(1)}s`);
  }
});

child.stderr.on("data", (chunk) => process.stderr.write(chunk));

async function waitForHttp() {
  for (let attempt = 0; attempt < 120; attempt++) {
    try {
      const res = await fetch(url, { redirect: "manual" });
      if (res.status < 500) {
        console.error(
          `[measure-dev-startup] HTTP ${res.status} at ${((Date.now() - started) / 1000).toFixed(1)}s (${useWebpack ? "webpack" : "turbopack"})`,
        );
        child.kill("SIGTERM");
        return;
      }
    } catch {
      // not up yet
    }
    await delay(500);
  }
  console.error("[measure-dev-startup] timed out waiting for HTTP");
  child.kill("SIGTERM");
  process.exitCode = 1;
}

void waitForHttp();
