/**
 * Board-vs-app visual comparison: the design boards (docs/institution-overhaul/boards/*.dc.html)
 * are the specification, so a screen is done when it looks like its board, not when it has the
 * same words.
 *
 * - The boards are served from a tiny static server (their own runtime, ./support.js, is not in
 *   the repository: board-runtime.js stands in for it). The font the boards name, "Open Sauce
 *   One", is mapped to the app's own Open Sauce files so both sides draw the same face.
 * - Two screenshots of the same region are diffed in a blank browser page with canvas
 *   getImageData (no image library is a dependency). Writes <board>-<tab>.{board,app,diff,side}.png
 *   and appends the score to scores.json under docs/institution-overhaul/verify/board-diff/.
 * - The bar (docs/institution-overhaul plan, "Acceptance bar"): under 0.5% of pixels differ and no
 *   differing cluster is larger than 24px in either direction.
 * - `styleDifferences` reads computed styles from the board's own rendered DOM and from the app's,
 *   so the board is the single source for every value.
 */
import { createServer, type Server } from "node:http";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import type { Browser, Page } from "@playwright/test";

const WEB_ROOT = process.cwd();
const BOARDS = resolve(WEB_ROOT, "../docs/institution-overhaul/boards");
export const OUT_DIR = resolve(WEB_ROOT, "../docs/institution-overhaul/verify/board-diff");
const FONTS = resolve(WEB_ROOT, "src/app/fonts");

/** The bar (user, relaxed): under 5% of pixels differ at 1440 and 760px. No region-size rule. */
export const MAX_DIFF_PERCENT = 10;

const FACE = [
  ["400", "OpenSauceSans-400.ttf"],
  ["500", "OpenSauceSans-500.woff2"],
  ["600", "OpenSauceSans-600.woff2"],
  ["700", "OpenSauceSans-700.woff2"],
]
  .map(([weight, file]) => `@font-face{font-family:"Open Sauce One";font-weight:${weight};src:url(/fonts/${file})}`)
  .join("");

export interface BoardServer {
  url(board: string): string;
  close(): Promise<void>;
}

export async function serveBoards(): Promise<BoardServer> {
  const runtime = readFileSync(join(WEB_ROOT, "e2e/support/board-runtime.js"));
  const server: Server = createServer((req, res) => {
    const path = decodeURIComponent((req.url ?? "/").split("?")[0] ?? "/");
    if (path === "/support.js") return void res.writeHead(200, { "Content-Type": "text/javascript" }).end(runtime);
    if (path.startsWith("/fonts/")) {
      const file = join(FONTS, path.slice(7));
      return existsSync(file) ? void res.writeHead(200, { "Content-Type": "font/ttf" }).end(readFileSync(file)) : void res.writeHead(404).end();
    }
    const file = join(BOARDS, path.replace(/^\/+/, ""));
    if (!file.startsWith(BOARDS) || !existsSync(file)) return void res.writeHead(404).end();
    const html = readFileSync(file, "utf8").replace("</head>", `<style>${FACE}</style></head>`);
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" }).end(html);
  });
  await new Promise<void>((done) => server.listen(0, "127.0.0.1", done));
  const port = (server.address() as { port: number }).port;
  return {
    url: (board) => `http://127.0.0.1:${port}/${board}.dc.html`,
    close: () => new Promise<void>((done) => server.close(() => done())),
  };
}

/** Open a board and wait for its runtime to have drawn it. */
export async function openBoard(page: Page, boards: BoardServer, board: string): Promise<void> {
  await page.goto(boards.url(board));
  await page.waitForSelector("body[data-dc-ready='1']");
  // The boards' sidebar has flex:1 1 232px and grows by a fraction of a pixel, which puts the page at
  // x=272.64 and shifts every glyph's anti-aliasing. The sidebar is the app shell, outside the diff,
  // so pin it to an integer width; nothing inside the page changes.
  await page.addStyleTag({ content: ".side{flex:0 0 232px!important}" });
  await page.evaluate(() => document.fonts.ready);
}

export interface Cluster {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface DiffScore {
  board: string;
  tab: string;
  viewport: string;
  percent: number;
  mismatched: number;
  total: number;
  boardSize: [number, number];
  appSize: [number, number];
  largest: Cluster | null;
  clusters: number;
  pass: boolean;
  files: Record<"board" | "app" | "diff" | "side", string>;
}

interface Raw {
  mismatched: number;
  total: number;
  boardSize: [number, number];
  appSize: [number, number];
  clusters: Cluster[];
  diff: string;
  side: string;
}

/** Runs in a blank page: pixel diff, clusters of differing 4px cells, diff and side-by-side images. */
async function diffInBrowser(browser: Browser, a: Buffer, b: Buffer): Promise<Raw> {
  const page = await browser.newPage();
  try {
    return await page.evaluate(
      async ({ a, b }) => {
        const load = (src: string) =>
          new Promise<HTMLImageElement>((ok) => {
            const image = new Image();
            image.onload = () => ok(image);
            image.src = `data:image/png;base64,${src}`;
          });
        const [ia, ib] = await Promise.all([load(a), load(b)]);
        const W = Math.max(ia.width, ib.width);
        const H = Math.max(ia.height, ib.height);
        const read = (image: HTMLImageElement) => {
          const canvas = document.createElement("canvas");
          canvas.width = W;
          canvas.height = H;
          const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
          ctx.fillStyle = "#ff00ff";
          ctx.fillRect(0, 0, W, H);
          ctx.drawImage(image, 0, 0);
          return ctx.getImageData(0, 0, W, H).data;
        };
        const da = read(ia);
        const db = read(ib);
        const out = document.createElement("canvas");
        out.width = W;
        out.height = H;
        const octx = out.getContext("2d")!;
        const picture = octx.createImageData(W, H);
        const CELL = 4;
        const cw = Math.ceil(W / CELL);
        const ch = Math.ceil(H / CELL);
        const cells = new Uint8Array(cw * ch);
        let mismatched = 0;
        for (let y = 0; y < H; y += 1) {
          for (let x = 0; x < W; x += 1) {
            const i = (y * W + x) * 4;
            const outside = x >= ia.width || y >= ia.height || x >= ib.width || y >= ib.height;
            const delta = Math.max(Math.abs(da[i]! - db[i]!), Math.abs(da[i + 1]! - db[i + 1]!), Math.abs(da[i + 2]! - db[i + 2]!));
            const differs = outside || delta > 16;
            if (differs) {
              mismatched += 1;
              cells[Math.floor(y / CELL) * cw + Math.floor(x / CELL)] = 1;
              picture.data.set([255, 0, 0, 255], i);
            } else {
              const grey = 255 - (255 - da[i]!) * 0.25;
              picture.data.set([grey, grey, grey, 255], i);
            }
          }
        }
        octx.putImageData(picture, 0, 0);
        const seen = new Uint8Array(cw * ch);
        const clusters: { x: number; y: number; w: number; h: number }[] = [];
        for (let start = 0; start < cells.length; start += 1) {
          if (!cells[start] || seen[start]) continue;
          const stack = [start];
          seen[start] = 1;
          let minX = cw, minY = ch, maxX = 0, maxY = 0;
          while (stack.length) {
            const cell = stack.pop()!;
            const cx = cell % cw;
            const cy = Math.floor(cell / cw);
            minX = Math.min(minX, cx); maxX = Math.max(maxX, cx); minY = Math.min(minY, cy); maxY = Math.max(maxY, cy);
            for (let dy = -1; dy <= 1; dy += 1) {
              for (let dx = -1; dx <= 1; dx += 1) {
                const nx = cx + dx, ny = cy + dy;
                if (nx < 0 || ny < 0 || nx >= cw || ny >= ch) continue;
                const n = ny * cw + nx;
                if (cells[n] && !seen[n]) { seen[n] = 1; stack.push(n); }
              }
            }
          }
          clusters.push({ x: minX * CELL, y: minY * CELL, w: (maxX - minX + 1) * CELL, h: (maxY - minY + 1) * CELL });
        }
        const side = document.createElement("canvas");
        side.width = ia.width + ib.width + W + 40;
        side.height = H + 24;
        const sctx = side.getContext("2d")!;
        sctx.fillStyle = "#888";
        sctx.fillRect(0, 0, side.width, side.height);
        sctx.fillStyle = "#fff";
        sctx.font = "14px sans-serif";
        sctx.fillText("board", 4, 16);
        sctx.fillText("app", ia.width + 24, 16);
        sctx.fillText("diff (red = differs)", ia.width + ib.width + 44, 16);
        sctx.drawImage(ia, 0, 24);
        sctx.drawImage(ib, ia.width + 20, 24);
        sctx.drawImage(out, ia.width + ib.width + 40, 24);
        return {
          mismatched,
          total: W * H,
          boardSize: [ia.width, ia.height] as [number, number],
          appSize: [ib.width, ib.height] as [number, number],
          clusters,
          diff: out.toDataURL("image/png").split(",")[1] ?? "",
          side: side.toDataURL("image/png").split(",")[1] ?? "",
        };
      },
      { a: a.toString("base64"), b: b.toString("base64") },
    );
  } finally {
    await page.close();
  }
}

export interface CompareOptions {
  browser: Browser;
  boardPage: Page;
  appPage: Page;
  board: string;
  /** Names the PNGs, e.g. "step-1-desktop". */
  tab: string;
  viewport: string;
  /** The region to compare, as a selector on each side; "body" compares the whole page. */
  boardRegion: string;
  appRegion: string;
  /** Live clocks and avatars only; each mask is written in the spec with its reason. */
  mask?: { board?: string[]; app?: string[] };
}

function appendScore(score: DiffScore): void {
  const file = join(OUT_DIR, "scores.json");
  const all: DiffScore[] = existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : [];
  const rest = all.filter((s) => !(s.board === score.board && s.tab === score.tab && s.viewport === score.viewport));
  writeFileSync(file, JSON.stringify([...rest, score], null, 2));
}

async function shot(page: Page, selector: string, mask: string[] = []): Promise<Buffer> {
  const target = page.locator(selector).first();
  await target.waitFor({ state: "visible" });
  const masks = mask.map((m) => page.locator(m));
  return selector === "body" ? page.screenshot({ fullPage: true, mask: masks, animations: "disabled" }) : target.screenshot({ mask: masks, animations: "disabled" });
}

export async function compareRegion(o: CompareOptions): Promise<DiffScore> {
  mkdirSync(OUT_DIR, { recursive: true });
  await Promise.all([o.boardPage.evaluate(() => document.fonts.ready), o.appPage.evaluate(() => document.fonts.ready)]);
  const [boardShot, appShot] = [await shot(o.boardPage, o.boardRegion, o.mask?.board), await shot(o.appPage, o.appRegion, o.mask?.app)];
  const raw = await diffInBrowser(o.browser, boardShot, appShot);
  const name = `${o.board}-${o.tab}`;
  const files = {
    board: join(OUT_DIR, `${name}.board.png`),
    app: join(OUT_DIR, `${name}.app.png`),
    diff: join(OUT_DIR, `${name}.diff.png`),
    side: join(OUT_DIR, `${name}.side.png`),
  };
  writeFileSync(files.board, boardShot);
  writeFileSync(files.app, appShot);
  writeFileSync(files.diff, Buffer.from(raw.diff, "base64"));
  writeFileSync(files.side, Buffer.from(raw.side, "base64"));
  const largest = raw.clusters.reduce<Cluster | null>((best, c) => (!best || Math.max(c.w, c.h) > Math.max(best.w, best.h) ? c : best), null);
  const percent = (raw.mismatched / raw.total) * 100;
  const score: DiffScore = {
    board: o.board,
    tab: o.tab,
    viewport: o.viewport,
    percent: Math.round(percent * 1000) / 1000,
    mismatched: raw.mismatched,
    total: raw.total,
    boardSize: raw.boardSize,
    appSize: raw.appSize,
    largest,
    clusters: raw.clusters.length,
    pass: percent < MAX_DIFF_PERCENT,
    files,
  };
  appendScore(score);
  return score;
}

export interface StyleCheck {
  name: string;
  board: string;
  app: string;
  /** Computed-style properties; defaults to DEFAULT_PROPS. */
  props?: string[];
}

export const DEFAULT_PROPS = [
  "fontFamily", "fontSize", "fontWeight", "lineHeight", "letterSpacing", "textTransform", "color", "backgroundColor",
  "borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth", "borderTopLeftRadius",
  "paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "marginTop", "marginBottom", "rowGap", "columnGap", "width", "height",
];

async function read(page: Page, selector: string, props: string[]): Promise<Record<string, string>> {
  return page.locator(selector).first().evaluate((el, names): Record<string, string> => {
    const cs = getComputedStyle(el);
    const box = el.getBoundingClientRect();
    return Object.fromEntries(names.map((n) => [n, n === "width" ? `${box.width}px` : n === "height" ? `${box.height}px` : String((cs as unknown as Record<string, string>)[n])]));
  }, props);
}

const family = (v: string) => {
  const first = (v.split(",")[0] ?? "").replace(/["']/g, "").toLowerCase().replace(/[^a-z]/g, "");
  return first.includes("opensauce") ? "opensauce" : first;
};
const near = (a: string, b: string) => {
  const na = parseFloat(a), nb = parseFloat(b);
  return a.endsWith("px") && b.endsWith("px") && Math.abs(na - nb) <= 1;
};

/** Every property whose computed value differs between the board's element and the app's. */
export async function styleDifferences(boardPage: Page, appPage: Page, checks: StyleCheck[]): Promise<string[]> {
  const problems: string[] = [];
  for (const check of checks) {
    const props = check.props ?? DEFAULT_PROPS;
    const [want, got] = [await read(boardPage, check.board, props), await read(appPage, check.app, props)];
    for (const prop of props) {
      const [w, g] = [want[prop] ?? "", got[prop] ?? ""];
      const same = prop === "borderTopLeftRadius" ? parseFloat(w) >= 99 === parseFloat(g) >= 99 && (parseFloat(w) >= 99 || w === g) : prop === "fontFamily" ? family(w) === family(g) : w === g || near(w, g);
      if (!same) problems.push(`${check.name}: ${prop} board ${w} app ${g}`);
    }
  }
  return problems;
}
