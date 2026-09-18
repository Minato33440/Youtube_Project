'use strict';
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { PNG } = require('pngjs');
const here = __dirname;
function png(file, width, height, paint) {
  const image = new PNG({ width, height }); paint(image.data, width, height);
  fs.writeFileSync(file, PNG.sync.write(image));
}
fs.mkdirSync(path.join(here, 'generated'), { recursive: true });
const generated = path.join(here, 'generated');
png(path.join(generated, 'eye_white.png'), 2, 1, (d) => { d[0] = d[1] = d[2] = 255; d[3] = 128; d[4] = d[5] = d[6] = 255; d[7] = 64; });
png(path.join(generated, 'iris_full.png'), 3, 1, (d) => { for (let i = 0; i < d.length; i += 4) { d[i + 2] = 255; d[i + 3] = 200; } });
const manifest = { canvas: { width: 8, height: 6 }, layers: [
  { name: 'eye_white', path: 'eye_white.png', left: 1, top: 1 }, { name: 'iris_full', path: 'iris_full.png', left: 0, top: 1, clipTo: 'eye_white' },
  { name: 'hidden_reference', path: 'iris_full.png', left: -1, top: 0, visible: false }
] };
const manifestFile = path.join(generated, 'manifest.json'); fs.writeFileSync(manifestFile, JSON.stringify(manifest, null, 2));
const result = spawnSync(process.execPath, [path.join(__dirname, '..', 'build_psd.js'), manifestFile, '--out-dir', generated], { encoding: 'utf8' });
if (result.status !== 0) throw new Error(result.stderr || result.stdout);
const report = JSON.parse(fs.readFileSync(path.join(generated, 'risa_parts_v1_verification.json'), 'utf8'));
if (report.status !== 'pass' || report.layerCount !== 3 || !report.roundTrip.rgba || !report.roundTrip.clipping || !report.layers[1].clipping) throw new Error('Unexpected verification report.');
const flat = PNG.sync.read(fs.readFileSync(path.join(generated, 'risa_parts_v1_flattened.png')));
const alphaAt = (x, y) => flat.data[(y * flat.width + x) * 4 + 3];
if (alphaAt(0, 1) !== 0 || alphaAt(1, 1) !== 178 || alphaAt(2, 1) !== 101) throw new Error(`Clipping alpha mismatch: ${alphaAt(0, 1)}, ${alphaAt(1, 1)}, ${alphaAt(2, 1)}`);
console.log('PSD smoke test passed:', report.psd);
