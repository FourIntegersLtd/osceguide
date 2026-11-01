// Will Vercel build the branch the promote workflow pushes?
//
// `Promote web to production` pushes a sha to a branch and waits for production to report it. If
// vercel.json's git.deploymentEnabled does not list that branch as true, a `"**": false` catch-all
// makes Vercel discard the push silently and the promote times out (production-web, 2026-10-25).
// The branch is read from the workflow's `git push origin "<sha>:refs/heads/<branch>"` line.
//
// Usage: node scripts/check-deploy-branches.mjs

import { resolve } from "node:path";
import { finish, read, root } from "./lib-src.mjs";

const workflow = ".github/workflows/promote-web.yml";
const PUSH_LINE = /git push\s+origin\s+"?[^\s":]*"?:refs\/heads\/([\w./-]+)/g; // the promote's only branch push
const pushed = [...read(resolve(root, "..", workflow)).matchAll(PUSH_LINE)].map((m) => m[1]);
const enabled = JSON.parse(read(resolve(root, "vercel.json"))).git?.deploymentEnabled ?? {};

// Both halves of the promote: main builds staging (the gate), the pushed branch builds production.
const lacks = (b) => `vercel.json git.deploymentEnabled lacks "${b}": true (a "**": false catch-all discards the push; ${workflow} then times out)`;
const offenders = [];
if (!pushed.length) offenders.push(`no git push to refs/heads/<branch> found in ${workflow}; the regex matches only that form, so update this check if the promote changed`);
for (const b of ["main", ...pushed]) if (enabled[b] !== true) offenders.push(lacks(b));

finish("check-deploy-branches", offenders);
