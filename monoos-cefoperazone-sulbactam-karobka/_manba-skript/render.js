// SVG -> PNG (preview) va vektor PDF. Ishlatish: node render.js <dir> [--png] [--pdf] [--dpi=200]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const dir = args[0];
const doPng = args.includes('--png');
const doPdf = args.includes('--pdf');
const dpiArg = args.find(a => a.startsWith('--dpi='));
const dpi = dpiArg ? Number(dpiArg.split('=')[1]) : 200;
const only = args.find(a => a.startsWith('--only='));

function walk(d) {
  return fs.readdirSync(d, { withFileTypes: true }).flatMap(e =>
    e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]);
}

(async () => {
  const browser = await chromium.launch();
  const files = walk(dir).filter(f => f.endsWith('.svg') && (!only || f.includes(only.split('=')[1])));
  for (const f of files) {
    const svg = fs.readFileSync(f, 'utf8');
    const m = svg.match(/<svg[^>]*width="([\d.]+)mm"[^>]*height="([\d.]+)mm"/);
    const wmm = Number(m[1]), hmm = Number(m[2]);
    const pxPerMm = dpi / 25.4;
    const wpx = Math.round(wmm * pxPerMm), hpx = Math.round(hmm * pxPerMm);
    const page = await browser.newPage({ viewport: { width: wpx, height: hpx } });
    const html = `<!doctype html><html><head><style>@page{size:${wmm}mm ${hmm}mm;margin:0}
      html,body{margin:0;padding:0}img{display:block;width:${wmm}mm;height:${hmm}mm}</style></head>
      <body><img src="file://${path.resolve(f)}"></body></html>`;
    const tmp = path.join(path.dirname(path.resolve(f)), '.render.html');
    if (doPng) {
      const pngHtml = html.replace(`width:${wmm}mm;height:${hmm}mm`, `width:${wpx}px;height:${hpx}px`);
      fs.writeFileSync(tmp, pngHtml);
      await page.goto('file://' + tmp);
      await page.waitForLoadState('load');
      await page.screenshot({ path: f.replace(/\.svg$/, '.png'), omitBackground: true });
    }
    if (doPdf) {
      // PDF uchun SVG'ni to'g'ridan-to'g'ri joylaymiz (img emas) - vektor saqlanadi
      const inline = `<!doctype html><html><head><style>@page{size:${wmm}mm ${hmm}mm;margin:0}
        html,body{margin:0;padding:0}svg{display:block;width:${wmm}mm;height:${hmm}mm}</style></head>
        <body>${svg.replace(/^<\?xml[^>]*>\s*/, '')}</body></html>`;
      fs.writeFileSync(tmp, inline);
      await page.goto('file://' + tmp);
      await page.pdf({ path: f.replace(/\.svg$/, '.pdf'), width: `${wmm}mm`, height: `${hmm}mm`,
        printBackground: true, pageRanges: '1' });
    }
    fs.existsSync(tmp) && fs.unlinkSync(tmp);
    await page.close();
    console.log('ok', path.relative(dir, f), wpx + 'x' + hpx);
  }
  await browser.close();
})();
