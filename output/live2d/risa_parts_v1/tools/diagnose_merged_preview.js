#!/usr/bin/env node
'use strict';

// Diagnose ag-psd's embedded merged preview as it would appear over solid backgrounds.
const fs = require('fs');
const { PNG } = require('pngjs');
const { readPsd, initializeCanvas } = require('ag-psd');

function createImageData(width, height) { return { width, height, data: new Uint8ClampedArray(width * height * 4) }; }
initializeCanvas(() => ({ getContext: () => ({ createImageData }) }), undefined, createImageData);

function color(hex) {
  if (!/^#[0-9a-f]{6}$/i.test(hex)) throw new Error(`Background must be #RRGGBB: ${hex}`);
  return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)];
}
function renderedChannel(rgb, alpha, background) { return rgb * (alpha / 255) + background * (1 - alpha / 255); }
function compare(expected, actual, background) {
  let visiblePixels = 0, sum = 0, channels = 0, max = 0, pixelsOver2 = 0;
  for (let i = 0; i < expected.length; i += 4) {
    if (expected[i + 3] === 0 && actual[i + 3] === 0) continue;
    visiblePixels++;
    let pixelOver2 = false;
    for (let c = 0; c < 3; c++) {
      const delta = Math.abs(renderedChannel(expected[i + c], expected[i + 3], background[c]) - renderedChannel(actual[i + c], actual[i + 3], background[c]));
      sum += delta; channels++; max = Math.max(max, delta); if (delta > 2) pixelOver2 = true;
    }
    if (pixelOver2) pixelsOver2++;
  }
  return { visiblePixels, maxVisiblePerChannelDifference: max, meanVisiblePerChannelDifference: channels ? sum / channels : 0, pixelsWithAnyChannelDifferenceOver2: pixelsOver2 };
}
function main() {
  const [psdFile, flattenedFile] = process.argv.slice(2);
  if (!psdFile || !flattenedFile || process.argv.includes('--help')) {
    console.log('Usage: node diagnose_merged_preview.js <parts.psd> <flattened.png>'); return;
  }
  const expected = PNG.sync.read(fs.readFileSync(flattenedFile));
  const psd = readPsd(fs.readFileSync(psdFile), { useImageData: true, skipThumbnail: true });
  if (!psd.imageData || psd.width !== expected.width || psd.height !== expected.height) throw new Error('PSD merged preview dimensions do not match flattened PNG.');
  const result = {
    psd: psdFile, flattenedPng: flattenedFile, canvas: { width: expected.width, height: expected.height },
    backgrounds: {
      '#F7F5F0': compare(expected.data, psd.imageData.data, color('#F7F5F0')),
      '#808080': compare(expected.data, psd.imageData.data, color('#808080'))
    }
  };
  console.log(JSON.stringify(result, null, 2));
}
try { main(); } catch (error) { console.error(`diagnose_merged_preview: ${error.message}`); process.exitCode = 1; }
