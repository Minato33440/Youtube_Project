'use strict';

// Writes exactly the two reference layers declared by reference_overlay_manifest.json.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { PNG } = require(path.resolve(__dirname, '../../../../../output/live2d/risa_parts_v1/tools/node_modules/pngjs'));
const { readPsd, writePsdBuffer, initializeCanvas } = require(path.resolve(__dirname, '../../../../../output/live2d/risa_parts_v1/tools/node_modules/ag-psd'));

function createImageData(width, height) { return { width, height, data: new Uint8ClampedArray(width * height * 4) }; }
initializeCanvas(() => ({ getContext: () => ({ createImageData }) }), undefined, createImageData);
const out = __dirname;
const manifest = JSON.parse(fs.readFileSync(path.join(out, 'reference_overlay_manifest.json'), 'utf8'));
const load = layer => {
  const png = PNG.sync.read(fs.readFileSync(path.join(out, layer.path)));
  return { name: layer.name, left: layer.left, top: layer.top, opacity: layer.opacity, imageData: { width: png.width, height: png.height, data: png.data } };
};
const children = manifest.layers.map(load);
const psdPath = path.join(out, 'oblique_nod_reference_overlay.psd');
fs.writeFileSync(psdPath, writePsdBuffer({ width: 4000, height: 6000, children }));
const read = readPsd(fs.readFileSync(psdPath), { useImageData: true, skipThumbnail: true });
const expected = manifest.layers;
const problems = [];
if (read.width !== 4000 || read.height !== 6000) problems.push('canvas dimensions');
if ((read.children || []).length !== 2) problems.push('layer count');
for (let i = 0; i < expected.length; i++) {
  const actual = read.children[i], wanted = expected[i];
  if (!actual || actual.name !== wanted.name) problems.push(`layer ${i} name`);
  if (!actual || actual.left !== wanted.left || actual.top !== wanted.top) problems.push(`layer ${i} position`);
  if (!actual || Math.abs(actual.opacity - wanted.opacity) > 0.01) problems.push(`layer ${i} opacity (${actual && actual.opacity})`);
  if (!actual || !actual.imageData || actual.imageData.width !== children[i].imageData.width || actual.imageData.height !== children[i].imageData.height) problems.push(`layer ${i} image dimensions`);
  if (actual && actual.imageData && !Buffer.from(actual.imageData.data).equals(Buffer.from(children[i].imageData.data))) problems.push(`layer ${i} RGBA read-back`);
}
const sha256 = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
manifest.artifact_sha256 = {
  psd: sha256(psdPath),
  reference_left_scaled_png: sha256(path.join(out, 'reference_left_scaled.png')),
  reference_right_mirrored_scaled_png: sha256(path.join(out, 'reference_right_mirrored_geometry_guide_scaled.png')),
  reference_left_fullcanvas_png: sha256(path.join(out, 'reference_left_fullcanvas.png')),
  reference_right_mirrored_fullcanvas_png: sha256(path.join(out, 'reference_right_mirrored_geometry_guide_fullcanvas.png')),
  case_01_reference_crop_comparison_png: sha256(path.join(out, 'case_01_reference_crop_comparison.png')),
};
fs.writeFileSync(path.join(out, 'reference_overlay_manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
const report = { status: problems.length ? 'fail' : 'pass', psd: psdPath, sha256: manifest.artifact_sha256.psd, canvas: [read.width, read.height], colorMode: read.colorMode, bitsPerChannel: read.bitsPerChannel, layers: (read.children || []).map(x => ({ name: x.name, left: x.left, top: x.top, opacity: x.opacity, dimensions: [x.imageData.width, x.imageData.height] })), checks: { canvas: !problems.includes('canvas dimensions'), layerCount: !problems.includes('layer count'), namesPositionsOpacityDimensionsAndRgba: !problems.some(x => x.startsWith('layer')) }, problems };
fs.writeFileSync(path.join(out, 'psd_readback_verification.json'), JSON.stringify(report, null, 2) + '\n');
if (problems.length) throw new Error(problems.join('; '));
process.stdout.write(JSON.stringify(report, null, 2) + '\n');
