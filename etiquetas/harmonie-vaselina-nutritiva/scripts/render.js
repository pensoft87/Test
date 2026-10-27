// Exports each variant of the label and of the sample sachet, as PNG and as a vector PDF:
//   etiqueta.html  6 x 2.5 in label,    designed at 1920 x 800, PNG at 320 ppi
//   muestra.html   2.3 x 1.5 in sachet, designed at 920 x 600 (400 ppi), PNG at 600 ppi
// usage: node scripts/render.js <out dir>
const path = require('path');
const { chromium } = require('playwright');

const VARIANTES = { 'sin-fragancia': 'vaselina-nutritiva-sin-fragancia', 'batana': 'vaselina-nutritiva-batana' };
const PIEZAS = [
  { html: 'etiqueta.html', name: n => `etiqueta-${n}-6x2.5in`, w: 1920, h: 800, dpr: 1, inW: 6, inH: 2.5 },
  { html: 'muestra.html', name: n => `sobrecito-muestra-${n}-2.3x1.5in`, w: 920, h: 600, dpr: 1.5, inW: 2.3, inH: 1.5 },
];
const out = process.argv[2] || '.';

(async () => {
  const browser = await chromium.launch();
  for (const p of PIEZAS) {
    const page = await browser.newPage({ viewport: { width: p.w, height: p.h }, deviceScaleFactor: p.dpr });
    const url = 'file://' + path.resolve(__dirname, '..', p.html);
    for (const [hash, name] of Object.entries(VARIANTES)) {
      await page.goto(url + '#' + hash);
      await page.reload();                                   // a hash-only change does not reload the page
      await page.evaluate(() => window.listo);
      await page.waitForLoadState('networkidle');
      const base = path.join(out, p.name(name));
      await page.screenshot({ path: base + '.png' });
      await page.pdf({ path: base + '.pdf', width: p.inW + 'in', height: p.inH + 'in', scale: p.inW * 96 / p.w,
                       printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 }, pageRanges: '1' });
      console.log(base);
    }
    await page.close();
  }
  await browser.close();
})();
