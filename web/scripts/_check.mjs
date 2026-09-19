import { chromium } from "playwright-core";
const BASE = "http://localhost:3100";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage();
const problems = [];
page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
page.on("console", (m) => { if (m.type() === "error") problems.push(`console: ${m.text().slice(0, 160)}`); });
await page.goto(BASE + "/login", { waitUntil: "networkidle" });
await page.fill('input[type="email"]', "walkthrough@example.com");
await page.fill('input[type="password"]', "correct horse battery");
await page.click('button[type="submit"]');
await page.waitForURL(/\/app\/\w/, { timeout: 15000 }).catch(() => {});
await page.waitForTimeout(800);
for (const path of process.argv.slice(2)) {
  const res = await page.goto(BASE + path, { waitUntil: "networkidle" });
  await page.waitForTimeout(1400);
  console.log(`\n=== ${path} [${res?.status()}] ${page.url().replace(BASE, "")}`);
  if (process.env.CLICK) await page.getByRole("tab", { name: process.env.CLICK }).click({ timeout: 8000 }).catch((e) => problems.push("click: " + e.message.slice(0, 80)));
  await page.waitForTimeout(1200);
  console.log((await page.innerText("body")).split("\n").filter(Boolean).slice(10, 48).join("\n"));
}
console.log("\n--- problems ---\n" + (problems.length ? [...new Set(problems)].slice(0, 10).join("\n") : "none"));
await browser.close();
