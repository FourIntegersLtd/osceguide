/**
 * platform-web compiles `frontend/src/b2b` and `frontend/src/shared` via
 * `externalDir` + turbopack `root`. Node resolves packages from the importer's
 * directory upward; `frontend/` has no install, so symlink its `node_modules`
 * to this app's.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const platformRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const repoRoot = path.join(platformRoot, "..");
const linkPath = path.join(repoRoot, "frontend/node_modules");
const targetPath = path.join(platformRoot, "node_modules");

if (!fs.existsSync(targetPath)) {
  console.error(
    "[ensure-legacy-frontend-node-modules] Run npm install in platform-web first.",
  );
  process.exit(1);
}

try {
  const stat = fs.lstatSync(linkPath);
  if (stat.isSymbolicLink()) {
    const current = fs.readlinkSync(linkPath);
    const expected = path.relative(path.dirname(linkPath), targetPath);
    if (path.resolve(path.dirname(linkPath), current) === targetPath) {
      process.exit(0);
    }
    fs.unlinkSync(linkPath);
  } else if (stat.isDirectory()) {
    console.warn(
      `[ensure-legacy-frontend-node-modules] ${linkPath} is a real directory; remove it and re-run dev.`,
    );
    process.exit(1);
  } else {
    fs.unlinkSync(linkPath);
  }
} catch (err) {
  if (err && typeof err === "object" && "code" in err && err.code !== "ENOENT") {
    throw err;
  }
}

const relativeTarget = path.relative(path.dirname(linkPath), targetPath);
fs.symlinkSync(relativeTarget, linkPath, "dir");
console.log(
  `[ensure-legacy-frontend-node-modules] linked frontend/node_modules → ${relativeTarget}`,
);
