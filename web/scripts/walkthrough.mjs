import { chromium } from "playwright-core";

const BASE = "http://localhost:3100";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage();
const problems = [];
page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
page.on("console", (m) => { if (m.type() === "error") problems.push(`console: ${m.text().slice(0,160)}`); });

async function show(label, path) {
  const res = await page.goto(BASE + path, { waitUntil: "networkidle" });
  // The session resolves in the browser, so a shell can still be a spinner
  // when the network goes quiet. Wait for it to settle before reading.
  await page.waitForTimeout(600);
  const nav = await page.$$eval("nav a", (as) => as.map((a) => a.textContent.trim()).filter(Boolean));
  const h1 = await page.$$eval("h1,h2", (hs) => hs.slice(0,2).map((h)=>h.textContent.trim()));
  console.log(`\n${label}  [${res?.status()}]  ${page.url().replace(BASE,"")}`);
  if (nav.length) console.log("  nav:", nav.join(" · "));
  if (h1.length) console.log("  heading:", h1.join(" | "));
}

await show("landing", "/");
await show("login", "/login");

// Sign in.
await page.fill('input[type="email"]', "walkthrough@example.com");
await page.fill('input[type="password"]', "correct horse battery");
await page.click('button[type="submit"]');
await page.waitForURL(/\/app\/\w/, { timeout: 15000 }).catch(() => {});
await page.waitForLoadState("networkidle");
await page.waitForTimeout(800);
console.log("\nafter sign-in ->", page.url().replace(BASE, ""));

await show("personal", "/app/me/dashboard");
await show("institution", "/app/kings/dashboard");
await show("partner", "/app/bmj/dashboard");
await show("staff", "/staff");
await show("consumer page on institution (should 404)", "/app/kings/mocks");
await show("workspace you are not in (should 404)", "/app/nowhere/dashboard");

console.log("\n--- problems ---");
console.log(problems.length ? [...new Set(problems)].slice(0,12).join("\n") : "none");
await browser.close();
