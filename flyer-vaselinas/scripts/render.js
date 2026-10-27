// Exports flyer.html: PNG at 600 ppi (2480 x 3508 = 105 x 148.5 mm, a quarter of A4) and a vector PDF.
// usage: node scripts/render.js <out dir>
const path = require('path');
const { chromium } = require('playwright');

const out = process.argv[2] || '.';
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1240, height: 1754 }, deviceScaleFactor: 2 });
  await page.goto('file://' + path.resolve(__dirname, '..', 'flyer.html'));
  await page.evaluate(() => window.listo);
  await page.waitForLoadState('networkidle');
  const base = path.join(out, 'flyer-vaselinas-harmonie-A6');
  await page.screenshot({ path: base + '.png' });
  // 105 mm = 396.85 CSS px, so the 1240 px design prints at a scale of 0.32004
  await page.pdf({ path: base + '.pdf', width: '105mm', height: '148.5mm', scale: 396.85 / 1240, printBackground: true,
                   margin: { top: 0, right: 0, bottom: 0, left: 0 }, pageRanges: '1' });
  console.log(base);
  await browser.close();
})();
