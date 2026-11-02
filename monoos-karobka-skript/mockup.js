// Quti + etiketka 3D maketi (faqat ko'rish uchun). node mockup.js <out_dir> <png>
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const out = path.resolve(process.argv[2]);
const png = path.resolve(process.argv[3]);
const S = 6.2; // px / mm
const W = 60, D = 36, H = 80, B = 3;
const u = f => 'file://' + path.join(out, f);
const face = (file, w, h, bleed) => `background-image:url('${u(file)}');` +
  `background-size:${(w + 2 * bleed) * S}px ${(h + 2 * bleed) * S}px;` +
  `background-position:${-bleed * S}px ${-bleed * S}px;`;
const html = `<!doctype html><html><head><style>
html,body{margin:0;background:linear-gradient(#eef1f5,#d9dee6);width:1500px;height:900px;overflow:hidden;font-family:sans-serif}
.scene{position:absolute;left:330px;top:150px;width:${W * S}px;height:${H * S}px;perspective:2200px}
.box{position:absolute;inset:0;transform-style:preserve-3d;transform:rotateX(-14deg) rotateY(34deg)}
.f{position:absolute;left:0;top:0;backface-visibility:hidden;background-repeat:no-repeat}
.front{width:${W * S}px;height:${H * S}px;transform:translateZ(${D * S / 2}px);${face('4-panellar/1-old-panel.svg', W, H, B)}}
.left{width:${D * S}px;height:${H * S}px;left:${(W - D) * S / 2}px;transform:rotateY(-90deg) translateZ(${W * S / 2}px);${face('4-panellar/2-yon-panel-tarkib.svg', D, H, 0)}}
.top{width:${W * S}px;height:${D * S}px;top:${(H - D) * S / 2}px;transform:rotateX(90deg) translateZ(${H * S / 2}px);${face('4-panellar/4-yuqori-qopqoq.svg', W, D, 0)}}
.left::after{content:'';position:absolute;inset:0;background:rgba(20,30,60,.10)}
.top::after{content:'';position:absolute;inset:0;background:rgba(255,255,255,.12)}
.shadow{position:absolute;left:240px;top:${150 + H * S + 18}px;width:${(W + D) * S + 120}px;height:60px;
  background:radial-gradient(ellipse at center,rgba(0,0,0,.28),rgba(0,0,0,0) 70%)}
.label{position:absolute;left:960px;top:250px;width:${90 * 5.6}px;height:${40 * 5.6}px;
  box-shadow:0 10px 30px rgba(0,0,0,.25);background:#fff url('${u('5-flakon-etiketka/etiketka-toliq.svg')}') no-repeat;
  background-size:${96 * 5.6}px ${46 * 5.6}px;background-position:${-3 * 5.6}px ${-3 * 5.6}px}
.cap{position:absolute;color:#556;font-size:18px}
</style></head><body>
<div class="shadow"></div>
<div class="scene"><div class="box"><div class="f top"></div><div class="f left"></div><div class="f front"></div></div></div>
<div class="label"></div>
<div class="cap" style="left:960px;top:500px">Flakon etiketkasi 90 × 40 mm (yoyilgan holda)</div>
<div class="cap" style="left:250px;top:${150 + H * S + 80}px">Karobka ${W} × ${D} × ${H} mm</div>
</body></html>`;
(async () => {
  const tmp = path.join(out, '.mockup.html');
  fs.writeFileSync(tmp, html);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1500, height: 900 }, deviceScaleFactor: 1.5 });
  await p.goto('file://' + tmp);
  await p.waitForTimeout(500);
  await p.screenshot({ path: png });
  await b.close();
  fs.unlinkSync(tmp);
  console.log('ok', png);
})();
