import { chromium } from 'playwright';
const b = await chromium.launch({executablePath: '/Users/yahayakenny/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell'});
const pages = ['/', '/exams/sca','/exams/plab','/exams/casc','/exams/ortho','/institutions','/pricing','/blogs'];
for (const w of [320, 375]) {
  const ctx = await b.newContext({ viewport: { width: w, height: 800 } });
  const p = await ctx.newPage(); const errs=[];
  p.on('pageerror', e => errs.push(e.message.slice(0,120)));
  for (const u of pages) {
    errs.length=0;
    try { await p.goto('http://localhost:3101'+u, { waitUntil: 'networkidle', timeout: 45000 }); } catch(e) { console.log(w,u,'NAV FAIL',e.message.slice(0,80)); continue; }
    const r = await p.evaluate(() => {
      const sw = document.documentElement.scrollWidth, cw = document.documentElement.clientWidth;
      const wide = [...document.querySelectorAll('body *')].filter(el => { const b = el.getBoundingClientRect(); return b.right > cw + 1 && b.width > 0 && getComputedStyle(el).position !== 'fixed' && !el.closest('[class*=overflow-x]'); }).slice(0,3).map(el => el.tagName + '.' + (el.className?.toString?.()||'').slice(0,60));
      return { sw, cw, nav: !!document.querySelector('nav, [role=navigation]'), footer: document.querySelectorAll('footer,[role=contentinfo]').length, wide };
    });
    console.log(w, u, r.sw > r.cw ? 'OVERFLOW' : 'ok', JSON.stringify(r), errs.join(' | '));
  }
  await ctx.close();
}
await b.close();
