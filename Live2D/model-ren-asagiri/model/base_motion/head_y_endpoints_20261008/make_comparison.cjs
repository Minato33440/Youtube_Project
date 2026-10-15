// Contact sheet of actual Editor screenshots; no retouching or pose synthesis.
const sharp = require('C:/Users/Setona/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const path = require('node:path');
const fs = require('node:fs/promises');
(async () => {
  const crops = [];
  for (const [i, name] of ['front', 'up', 'down'].entries()) {
    const input = await sharp(path.join(__dirname, name + '_editor.png'))
      .extract({left: 1060, top: 180, width: 600, height: 720}).png().toBuffer();
    crops.push({input, left: 20 + i * 620, top: 90});
  }
  const labels = Buffer.from(`<svg width="1880" height="850"><style>text{font-family:Arial,sans-serif;fill:#243049}</style>
  <text x="24" y="30" font-size="22">Ren_base7(2) | Y endpoint draft | X=0 / Z=0 | Cubism Editor 52.2%</text>
  <text x="24" y="67" font-size="24">FRONT   Y=0</text><text x="644" y="67" font-size="24">UP   Y=+30</text><text x="1264" y="67" font-size="24">DOWN   Y=-30</text>
  <text x="24" y="836" font-size="18">Same viewport / same crop. Actual editor captures. Endpoint shape and chin shading await manual review.</text></svg>`);
  await sharp({create:{width:1880,height:850,channels:4,background:'#edf1f6'}})
    .composite([...crops,{input:labels,left:0,top:0}]).png().toFile(path.join(__dirname,'Y_endpoint_comparison.png'));
  console.log('Saved Y_endpoint_comparison.png (equal-scale unretouched Editor crops).');
})().catch(e=>{console.error(e);process.exit(1)});
