// Uso: node render.js <archivo.html> <salida.png> <ancho> <alto> [escala]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [, , html, out, w, h, scale] = process.argv;
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: +w, height: +h },
    deviceScaleFactor: +(scale || 1),
  });
  await page.goto('file://' + path.resolve(html));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  await page.screenshot({ path: out, clip: { x: 0, y: 0, width: +w, height: +h } });
  await browser.close();
})();
