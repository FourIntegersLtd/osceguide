// Node test-runner resolver: adds .ts/.tsx/index.ts and maps "@/" to src so
// extensionless TypeScript imports work under Node's built-in type stripping.
import { existsSync, statSync } from "node:fs";
import { dirname, resolve as resolvePath } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SRC = resolvePath(dirname(fileURLToPath(import.meta.url)), "../src");
const EXTS = [".ts", ".tsx", ".mts", ".js", ".mjs"];

const isFile = (p) => existsSync(p) && statSync(p).isFile();

function tryCandidates(base) {
  if (isFile(base)) return base;
  for (const ext of EXTS) if (isFile(base + ext)) return base + ext;
  for (const ext of EXTS) if (isFile(`${base}/index${ext}`)) return `${base}/index${ext}`;
  return null;
}

export async function resolve(specifier, context, nextResolve) {
  let target = null;

  if (specifier.startsWith("@/")) {
    target = tryCandidates(resolvePath(SRC, specifier.slice(2)));
  } else if (specifier.startsWith(".")) {
    const parent = context.parentURL ? dirname(fileURLToPath(context.parentURL)) : process.cwd();
    target = tryCandidates(resolvePath(parent, specifier));
  }

  if (target) {
    // Node strips types only when it is told the source is TypeScript; saying
    // plain "module" hands it a .ts file to parse as JavaScript, which fails on
    // the first `export type`.
    const format = /\.(ts|mts|tsx)$/.test(target) ? "module-typescript" : "module";
    return { url: pathToFileURL(target).href, format, shortCircuit: true };
  }
  return nextResolve(specifier, context);
}
