#!/usr/bin/env node
'use strict';

/*
 * Packages PNG RGBA Live2D parts into a standard RGB, 8-bit PSD.
 * Input layer order is bottom-to-top. Cubism consumes PSD layer records in
 * reverse order, so write the manifest order directly to obtain its top-to-
 * bottom display order.
 */
const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const { readPsd, writePsdBuffer, initializeCanvas } = require('ag-psd');

// This packer works directly with un-premultiplied imageData. ag-psd still
// needs an ImageData factory for PSD read-back, but no drawing canvas.
function createImageData(width, height) { return { width, height, data: new Uint8ClampedArray(width * height * 4) }; }
initializeCanvas(
  () => ({ getContext: () => ({ createImageData }) }),
  undefined,
  createImageData
);

function fail(message) { throw new Error(message); }
function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (error) { fail(`Cannot read manifest ${file}: ${error.message}`); }
}
function positiveInt(value, label) {
  if (!Number.isInteger(value) || value <= 0) fail(`${label} must be a positive integer.`);
  return value;
}
function integer(value, label) {
  if (!Number.isInteger(value)) fail(`${label} must be an integer.`);
  return value;
}
function loadPng(file, label) {
  try {
    const png = PNG.sync.read(fs.readFileSync(file));
    if (!png.data || png.data.length !== png.width * png.height * 4) fail('decoded data is not RGBA');
    return png;
  } catch (error) { fail(`Cannot load ${label} PNG '${file}': ${error.message}`); }
}
function parseColor(value) {
  const text = value || '#808080';
  if (!/^#[0-9a-fA-F]{6}$/.test(text)) fail(`previewBackground must be #RRGGBB, got '${text}'.`);
  return [parseInt(text.slice(1, 3), 16), parseInt(text.slice(3, 5), 16), parseInt(text.slice(5, 7), 16)];
}
function alphaSummary(data, width, height, left, top) {
  let pixels = 0, minX = null, minY = null, maxX = null, maxY = null;
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    if (data[(y * width + x) * 4 + 3] === 0) continue;
    pixels++;
    const dx = left + x, dy = top + y;
    minX = minX === null ? dx : Math.min(minX, dx); minY = minY === null ? dy : Math.min(minY, dy);
    maxX = maxX === null ? dx : Math.max(maxX, dx); maxY = maxY === null ? dy : Math.max(maxY, dy);
  }
  return { nonTransparentPixels: pixels, contentBounds: pixels ? { left: minX, top: minY, right: maxX + 1, bottom: maxY + 1 } : null };
}
function blendSourceOver(dst, index, sr, sg, sb, sa) {
  const da = dst[index + 3] / 255, sourceA = sa / 255;
  const outA = sourceA + da * (1 - sourceA);
  if (outA === 0) { dst[index] = dst[index + 1] = dst[index + 2] = dst[index + 3] = 0; return; }
  dst[index] = Math.round((sr * sourceA + dst[index] * da * (1 - sourceA)) / outA);
  dst[index + 1] = Math.round((sg * sourceA + dst[index + 1] * da * (1 - sourceA)) / outA);
  dst[index + 2] = Math.round((sb * sourceA + dst[index + 2] * da * (1 - sourceA)) / outA);
  dst[index + 3] = Math.round(outA * 255);
}
function composite(canvas, layers) {
  const data = Buffer.alloc(canvas.width * canvas.height * 4);
  for (const layer of layers) {
    if (!layer.visible) continue;
    for (let y = 0; y < layer.png.height; y++) for (let x = 0; x < layer.png.width; x++) {
      const dx = layer.left + x, dy = layer.top + y;
      if (dx < 0 || dy < 0 || dx >= canvas.width || dy >= canvas.height) continue;
      const si = (y * layer.png.width + x) * 4, di = (dy * canvas.width + dx) * 4;
      let alpha = layer.png.data[si + 3];
      if (layer.clipBase) {
        const bx = dx - layer.clipBase.left, by = dy - layer.clipBase.top;
        const baseAlpha = bx < 0 || by < 0 || bx >= layer.clipBase.png.width || by >= layer.clipBase.png.height
          ? 0 : layer.clipBase.png.data[(by * layer.clipBase.png.width + bx) * 4 + 3];
        alpha = Math.round(alpha * baseAlpha / 255);
      }
      blendSourceOver(data, di, layer.png.data[si], layer.png.data[si + 1], layer.png.data[si + 2], alpha);
    }
  }
  return { width: canvas.width, height: canvas.height, data };
}
function rgbaEqual(a, b) { return a.length === b.length && a.every((v, i) => v === b[i]); }
function imageDifference(expected, actual) {
  let pixels = 0, visiblePixels = 0, transparentPixels = 0, alphaPixels = 0, maxChannelDelta = 0;
  for (let i = 0; i < expected.length; i += 4) {
    const changed = expected[i] !== actual[i] || expected[i + 1] !== actual[i + 1] || expected[i + 2] !== actual[i + 2] || expected[i + 3] !== actual[i + 3];
    if (!changed) continue;
    pixels++;
    if (expected[i + 3] || actual[i + 3]) visiblePixels++; else transparentPixels++;
    if (expected[i + 3] !== actual[i + 3]) alphaPixels++;
    maxChannelDelta = Math.max(maxChannelDelta,
      Math.abs(expected[i] - actual[i]), Math.abs(expected[i + 1] - actual[i + 1]),
      Math.abs(expected[i + 2] - actual[i + 2]), Math.abs(expected[i + 3] - actual[i + 3]));
  }
  return { exact: pixels === 0, pixels, visiblePixels, transparentPixels, alphaPixels, maxChannelDelta };
}
function writePng(file, image) { fs.writeFileSync(file, PNG.sync.write(image)); }
function resolveOutput(value, fallback, manifestDir, outDir) {
  return path.resolve(outDir || manifestDir, value || fallback);
}

function build(manifestFile, outDir) {
  const absoluteManifest = path.resolve(manifestFile), manifestDir = path.dirname(absoluteManifest);
  const manifest = readJson(absoluteManifest);
  if (!manifest.canvas || !Array.isArray(manifest.layers) || manifest.layers.length === 0) fail('Manifest requires canvas and a non-empty layers array.');
  const canvas = { width: positiveInt(manifest.canvas.width, 'canvas.width'), height: positiveInt(manifest.canvas.height, 'canvas.height') };
  const layers = manifest.layers.map((item, index) => {
    if (!item || typeof item.name !== 'string' || !item.name.trim()) fail(`layers[${index}].name must be a non-empty string.`);
    if (typeof item.path !== 'string' || !item.path) fail(`layers[${index}].path must be a PNG path.`);
    const source = path.resolve(manifestDir, item.path), png = loadPng(source, `layers[${index}]`);
    const left = integer(item.left, `layers[${index}].left`), top = integer(item.top, `layers[${index}].top`);
    if (item.clipTo !== undefined && (typeof item.clipTo !== 'string' || !item.clipTo.trim())) fail(`layers[${index}].clipTo must be a non-empty layer name when supplied.`);
    return { name: item.name, source, png, left, top, visible: item.visible !== false, clipTo: item.clipTo };
  });
  layers.forEach((layer, index) => {
    if (!layer.clipTo) return;
    const namedTarget = layers.find(candidate => candidate.name === layer.clipTo);
    if (!namedTarget) fail(`layers[${index}].clipTo '${layer.clipTo}' does not name a layer.`);
    if (index === 0 || layers[index - 1].name !== layer.clipTo) {
      fail(`layers[${index}].clipTo '${layer.clipTo}' must name the immediately preceding bottom-to-top layer.`);
    }
    layer.clipBase = layers[index - 1];
  });
  const output = manifest.output || {};
  const destination = outDir ? path.resolve(outDir) : manifestDir;
  fs.mkdirSync(destination, { recursive: true });
  const psdFile = resolveOutput(output.psd, 'risa_parts_v1.psd', manifestDir, destination);
  const flatFile = resolveOutput(output.flattenedPng, 'risa_parts_v1_flattened.png', manifestDir, destination);
  const previewFile = resolveOutput(output.previewPng, 'risa_parts_v1_preview.png', manifestDir, destination);
  const verificationFile = resolveOutput(output.verificationJson, 'risa_parts_v1_verification.json', manifestDir, destination);
  const flattened = composite(canvas, layers);
  const psd = {
    width: canvas.width, height: canvas.height,
    imageData: { width: canvas.width, height: canvas.height, data: flattened.data },
    children: layers.map(layer => ({ name: layer.name, left: layer.left, top: layer.top, hidden: !layer.visible, clipping: Boolean(layer.clipTo),
      imageData: { width: layer.png.width, height: layer.png.height, data: layer.png.data } }))
  };
  fs.writeFileSync(psdFile, writePsdBuffer(psd));
  writePng(flatFile, flattened);
  const [br, bg, bb] = parseColor(output.previewBackground);
  const preview = { width: canvas.width, height: canvas.height, data: Buffer.alloc(canvas.width * canvas.height * 4) };
  for (let i = 0; i < flattened.data.length; i += 4) {
    const a = flattened.data[i + 3] / 255;
    preview.data[i] = Math.round(flattened.data[i] * a + br * (1 - a));
    preview.data[i + 1] = Math.round(flattened.data[i + 1] * a + bg * (1 - a));
    preview.data[i + 2] = Math.round(flattened.data[i + 2] * a + bb * (1 - a)); preview.data[i + 3] = 255;
  }
  writePng(previewFile, preview);
  // ag-psd read-back validates the written PSD rather than merely the input manifest.
  const roundTrip = readPsd(fs.readFileSync(psdFile), { useImageData: true, skipThumbnail: true });
  const readLayers = roundTrip.children || [];
  const expected = layers;
  const problems = [];
  if (roundTrip.width !== canvas.width || roundTrip.height !== canvas.height) problems.push('canvas dimensions changed after PSD read-back');
  if (roundTrip.colorMode !== 3 || roundTrip.bitsPerChannel !== 8) problems.push(`PSD mode changed (colorMode=${roundTrip.colorMode}, bits=${roundTrip.bitsPerChannel})`);
  if (readLayers.length !== expected.length) problems.push(`layer count changed (${readLayers.length} != ${expected.length})`);
  for (let i = 0; i < Math.min(readLayers.length, expected.length); i++) {
    const actual = readLayers[i], wanted = expected[i];
    if (actual.name !== wanted.name) problems.push(`layer ${i} name changed`);
    if (actual.left !== wanted.left || actual.top !== wanted.top) problems.push(`layer ${i} placement changed`);
    if (Boolean(actual.hidden) !== !wanted.visible) problems.push(`layer ${i} visibility changed`);
    if (Boolean(actual.clipping) !== Boolean(wanted.clipTo)) problems.push(`layer ${i} clipping flag changed`);
    const actualData = actual.imageData && actual.imageData.data;
    if (!actual.imageData || actual.imageData.width !== wanted.png.width || actual.imageData.height !== wanted.png.height || !rgbaEqual(actualData, wanted.png.data)) problems.push(`layer ${i} RGBA changed`);
  }
  // Recompose the layer pixels returned by ag-psd. This is the actual visual
  // payload of the PSD and catches visible differences without relying on its
  // separate, lossy merged-preview alpha conversion.
  const readBackBottomToTop = layers.map((wanted, index) => {
    const actual = readLayers[index];
    return { name: actual.name, png: actual.imageData, left: actual.left, top: actual.top, visible: !actual.hidden, clipTo: wanted.clipTo };
  });
  readBackBottomToTop.forEach((layer, index) => { if (layer.clipTo) layer.clipBase = readBackBottomToTop[index - 1]; });
  const layerComposite = composite(canvas, readBackBottomToTop);
  if (!rgbaEqual(layerComposite.data, flattened.data)) problems.push('visible flattened RGBA changed when recompositing PSD read-back layers');
  if (problems.length) fail(`PSD round-trip verification failed: ${problems.join('; ')}`);
  const embeddedComposite = roundTrip.imageData
    ? imageDifference(flattened.data, roundTrip.imageData.data)
    : { exact: false, unavailable: true };
  const report = {
    status: 'pass', library: 'ag-psd', psd: psdFile, flattenedPng: flatFile, previewPng: previewFile,
    canvas, layerCount: layers.length, inputOrder: 'bottom-to-top', psdRecordOrder: 'bottom-to-top (Cubism-compatible)',
    layers: layers.map(layer => ({ name: layer.name, path: layer.source, visible: layer.visible, clipTo: layer.clipTo || null, clipping: Boolean(layer.clipTo),
      bounds: { left: layer.left, top: layer.top, right: layer.left + layer.png.width, bottom: layer.top + layer.png.height },
      alpha: alphaSummary(layer.png.data, layer.png.width, layer.png.height, layer.left, layer.top) })),
    roundTrip: { verifiedWith: 'ag-psd readPsd(useImageData)', colorMode: 'RGB (3)', bitsPerChannel: 8,
      dimensions: true, names: true, positions: true, visibility: true, clipping: true, rgba: true,
      renderedLayerCompositeRgba: true,
      embeddedCompositeReadback: embeddedComposite,
      embeddedCompositeNote: embeddedComposite.exact ? null : 'ag-psd applies its white-matte conversion to the separate merged preview. Layer RGBA is exact and recomposites exactly to the emitted flattened PNG; the diagnostic above is retained rather than treated as a transparent-pixel-only difference.' }
  };
  fs.writeFileSync(verificationFile, JSON.stringify(report, null, 2) + '\n');
  process.stdout.write(JSON.stringify({ status: report.status, psd: psdFile, verification: verificationFile }, null, 2) + '\n');
}

function main() {
  const args = process.argv.slice(2);
  if (!args[0] || args.includes('--help')) {
    process.stdout.write('Usage: node build_psd.js <manifest.json> [--out-dir <directory>]\n'); return;
  }
  const outIndex = args.indexOf('--out-dir');
  if (outIndex !== -1 && (!args[outIndex + 1] || outIndex + 2 !== args.length)) fail('Use --out-dir followed by one directory path.');
  if (outIndex === -1 && args.length !== 1) fail('Unexpected arguments. Use --help for usage.');
  build(args[0], outIndex === -1 ? undefined : args[outIndex + 1]);
}
try { main(); } catch (error) { process.stderr.write(`build_psd: ${error.message}\n`); process.exitCode = 1; }
