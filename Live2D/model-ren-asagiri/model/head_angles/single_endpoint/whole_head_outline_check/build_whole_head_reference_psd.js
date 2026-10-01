'use strict';

// Build an isolated Cubism reference PSD.  Source art, cmo3 and runtimes are
// read-only; every output stays in whole_head_outline_check.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { PNG } = require(path.resolve(__dirname, '../../../../../../output/live2d/risa_parts_v1/tools/node_modules/pngjs'));
const { readPsd, writePsdBuffer, initializeCanvas } = require(path.resolve(__dirname, '../../../../../../output/live2d/risa_parts_v1/tools/node_modules/ag-psd'));

function imageData(width, height) {
  return { width, height, data: new Uint8ClampedArray(width * height * 4) };
}
initializeCanvas(() => ({ getContext: () => ({ createImageData: imageData }) }), undefined, imageData);

const sha256 = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const targetPath = path.join(__dirname, 'whole_head_contour_target.json');
const target = JSON.parse(fs.readFileSync(targetPath, 'utf8'));
const psdPath = path.join(__dirname, 'whole_head_reference_4000x6000.psd');
const manifestPath = path.join(__dirname, 'whole_head_reference_psd_manifest.json');
const readbackPath = path.join(__dirname, 'whole_head_reference_psd_readback.json');
const canvas = [4000, 6000];

function pngLayer(name, asset, opacity) {
  const file = path.join(__dirname, asset.path);
  const png = PNG.sync.read(fs.readFileSync(file));
  if (png.width !== asset.dimensions_px[0] || png.height !== asset.dimensions_px[1]) {
    throw new Error(`${name}: PNG dimensions differ from target metadata`);
  }
  return {
    name,
    left: asset.left,
    top: asset.top,
    opacity,
    imageData: { width: png.width, height: png.height, data: png.data },
    source: file,
  };
}

const assets = target.psd_layer_assets;
const layers = [
  pngLayer('GUIDE__FACE_UNDERFILL_OBSERVED__CYAN__HIDE_BEFORE_EXPORT', assets.face_guide, 1),
  pngLayer('GUIDE__SCALP_HAIR_HIDDEN_INFERRED__AMBER_DASHED__HIDE_BEFORE_EXPORT', assets.scalp_guide, 1),
  pngLayer('GUIDE__EAR_OUTER_SEPARATE__MAGENTA__DO_NOT_TRACE_AS_FACE', assets.ear_guide, 1),
  pngLayer('REFERENCE__BOSS_OUTLINE_REGISTERED__85PCT__HIDE_BEFORE_EXPORT', assets.outline, 0.85),
  pngLayer('REFERENCE__ROUGH_EXACT_CROP__25PCT__HIDE_BEFORE_EXPORT', assets.rough, 0.25),
];

fs.writeFileSync(psdPath, writePsdBuffer({ width: canvas[0], height: canvas[1], children: layers }));
const read = readPsd(fs.readFileSync(psdPath), { useImageData: true, skipThumbnail: true });
const problems = [];
if (read.width !== canvas[0] || read.height !== canvas[1]) problems.push('canvas dimensions');
if ((read.children || []).length !== layers.length) problems.push('layer count');
for (let i = 0; i < layers.length; i++) {
  const actual = read.children && read.children[i];
  const expected = layers[i];
  if (!actual || actual.name !== expected.name) problems.push(`layer ${i} name`);
  if (!actual || actual.left !== expected.left || actual.top !== expected.top) problems.push(`layer ${i} position`);
  if (!actual || Math.abs(actual.opacity - expected.opacity) > 0.01) problems.push(`layer ${i} opacity`);
  if (!actual || !actual.imageData || actual.imageData.width !== expected.imageData.width || actual.imageData.height !== expected.imageData.height) problems.push(`layer ${i} dimensions`);
  if (actual && actual.imageData && !Buffer.from(actual.imageData.data).equals(Buffer.from(expected.imageData.data))) problems.push(`layer ${i} RGBA readback`);
}

const manifest = {
  purpose: 'Import-only 4000x6000 whole-head reference for face-underfill adjustment. Hide every layer before model export.',
  target: { path: targetPath, sha256: sha256(targetPath) },
  inputs: target.inputs,
  registration: target.registration,
  classification: target.classification,
  canvas,
  layers: layers.map(layer => ({
    name: layer.name,
    left: layer.left,
    top: layer.top,
    opacity: layer.opacity,
    dimensions_px: [layer.imageData.width, layer.imageData.height],
    source: path.basename(layer.source),
    source_sha256: sha256(layer.source),
  })),
  psd: path.basename(psdPath),
  psd_sha256: sha256(psdPath),
};
fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
const report = {
  status: problems.length ? 'fail' : 'pass',
  psd: psdPath,
  sha256: manifest.psd_sha256,
  canvas: [read.width, read.height],
  colorMode: read.colorMode,
  bitsPerChannel: read.bitsPerChannel,
  layers: (read.children || []).map(layer => ({
    name: layer.name,
    left: layer.left,
    top: layer.top,
    opacity: layer.opacity,
    dimensions_px: layer.imageData ? [layer.imageData.width, layer.imageData.height] : null,
  })),
  checks: {
    canvas: !problems.includes('canvas dimensions'),
    layerCount: !problems.includes('layer count'),
    namesPositionsOpacityDimensionsAndRgba: !problems.some(problem => problem.startsWith('layer')),
  },
  problems,
};
fs.writeFileSync(readbackPath, JSON.stringify(report, null, 2) + '\n');
if (problems.length) throw new Error(problems.join('; '));
process.stdout.write(JSON.stringify(report, null, 2) + '\n');
