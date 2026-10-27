// Exports each variant of etiqueta.html: PNG at 320 ppi (1920 x 800) and a vector PDF of 6 x 2.5 in.
// usage: node scripts/render.js <out dir>
const path = require('path');
const { chromium } = require('playwright');

const VARIANTES = { 'sin-fragancia': 'vaselina-nutritiva-sin-fragancia', 'batana': 'vaselina-nutritiva-batana' };
const out = process.argv[2] || '.';
const page_ = 'file://' + path.resolve(__dirname, '..', 'etiqueta.html');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 800 }, deviceScaleFactor: 1 });
  for (const [hash, name] of Object.entries(VARIANTES)) {
    await page.goto(page_ + '#' + hash);
    await page.reload();                                     // a hash-only change does not reload the page
    await page.evaluate(() => window.listo);
    await page.waitForLoadState('networkidle');
    const base = path.join(out, `etiqueta-${name}-6x2.5in`);
    await page.screenshot({ path: base + '.png' });
    await page.pdf({ path: base + '.pdf', width: '6in', height: '2.5in', scale: 0.3, printBackground: true,
                     margin: { top: 0, right: 0, bottom: 0, left: 0 }, pageRanges: '1' });
    console.log(base);
  }
  await browser.close();
})();
