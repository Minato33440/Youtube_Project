'use strict';

// Builds a non-destructive Cubism placement guide.  It never rewrites either
// the source illustration or the model: all artwork below is transparent-line
// raster data positioned in the established 4000 x 6000 reference canvas.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { PNG } = require(path.resolve(__dirname, '../../../../../../output/live2d/risa_parts_v1/tools/node_modules/pngjs'));
const { readPsd, writePsdBuffer, initializeCanvas } = require(path.resolve(__dirname, '../../../../../../output/live2d/risa_parts_v1/tools/node_modules/ag-psd'));

function createImageData(width, height) { return { width, height, data: new Uint8ClampedArray(width * height * 4) }; }
initializeCanvas(() => ({ getContext: () => ({ createImageData }) }), undefined, createImageData);

const guideDir = __dirname;
const headAnglesDir = path.resolve(guideDir, '../..');
const referenceDir = path.join(headAnglesDir, 'reference_overlay');
const guideJsonPath = path.join(guideDir, 'looking_down_2_source_landmark_guide.json');
const guideManifestPath = path.join(guideDir, 'contour_guide_psd_manifest.json');
const verificationPath = path.join(guideDir, 'contour_guide_psd_readback.json');
const psdPath = path.join(guideDir, 'looking_down_2_contour_guide_4000x6000.psd');
const CANVAS = [4000, 6000];
const SCALE = 1.2904500571168767;
const OFFSET = [1404.826424299698, 161.11685212010656];
const sourceToCanvas = ([x, y]) => [OFFSET[0] + x * SCALE, OFFSET[1] + y * SCALE];
const sha256 = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');

const sourceManifest = JSON.parse(fs.readFileSync(path.join(referenceDir, 'reference_overlay_manifest.json'), 'utf8'));
const guide = JSON.parse(fs.readFileSync(guideJsonPath, 'utf8'));
const sourcePath = guide.source.path;
if (sha256(sourcePath) !== sourceManifest.source.sha256) throw new Error('Source hash no longer matches reference overlay manifest; refusing to build guide.');
if (Math.abs(sourceManifest.alignment.full_canvas_scale - SCALE) > 1e-12 || sourceManifest.alignment.full_canvas_offset[0] !== OFFSET[0] || sourceManifest.alignment.full_canvas_offset[1] !== OFFSET[1]) {
  throw new Error('Reference transform differs from the reviewed placement; refusing to silently substitute it.');
}

function setPx(image, x, y, rgba) {
  if (x < 0 || y < 0 || x >= image.width || y >= image.height) return;
  const i = (Math.round(y) * image.width + Math.round(x)) * 4;
  image.data[i] = rgba[0]; image.data[i + 1] = rgba[1]; image.data[i + 2] = rgba[2]; image.data[i + 3] = rgba[3];
}
function disc(image, x, y, radius, rgba) {
  for (let yy = Math.floor(y - radius); yy <= Math.ceil(y + radius); yy++) {
    for (let xx = Math.floor(x - radius); xx <= Math.ceil(x + radius); xx++) {
      if ((xx - x) ** 2 + (yy - y) ** 2 <= radius ** 2) setPx(image, xx, yy, rgba);
    }
  }
}
function line(image, a, b, radius, rgba, dash) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const steps = Math.max(1, Math.ceil(Math.hypot(dx, dy)));
  for (let i = 0; i <= steps; i++) {
    if (dash && (i % 24) >= 14) continue;
    disc(image, a[0] + dx * i / steps, a[1] + dy * i / steps, radius, rgba);
  }
}
function bounds(points, pad) {
  const xy = points.map(p => sourceToCanvas(p.source_px));
  return {
    left: Math.floor(Math.min(...xy.map(p => p[0])) - pad),
    top: Math.floor(Math.min(...xy.map(p => p[1])) - pad),
    right: Math.ceil(Math.max(...xy.map(p => p[0])) + pad),
    bottom: Math.ceil(Math.max(...xy.map(p => p[1])) + pad),
  };
}
function localImage(box) { return createImageData(box.right - box.left + 1, box.bottom - box.top + 1); }
function local(point, box) { const p = sourceToCanvas(point.source_px); return [p[0] - box.left, p[1] - box.top]; }

const contour = guide.visible_facial_skin_outer_contour.points;
const observed = contour.filter(p => p.reliability === 'observed');
const inferredRight = contour.slice(0, contour.findIndex(p => p.reliability === 'observed') + 1);
const firstLeftInferred = contour.findIndex(p => p.id === 'l_occlusion_1');
const inferredLeft = contour.slice(firstLeftInferred - 1);
const contourBox = bounds(contour, 24);
const cyan = [0, 229, 255, 255], amber = [255, 178, 46, 255], magenta = [255, 68, 210, 255];
const observedImage = localImage(contourBox);
const inferredImage = localImage(contourBox);
for (let i = 1; i < observed.length; i++) line(observedImage, local(observed[i - 1], contourBox), local(observed[i], contourBox), 2, cyan, false);
for (const p of observed) { const q = local(p, contourBox); disc(observedImage, q[0], q[1], 3, cyan); }
for (const section of [inferredRight, inferredLeft]) {
  for (let i = 1; i < section.length; i++) line(inferredImage, local(section[i - 1], contourBox), local(section[i], contourBox), 2, amber, true);
  for (const p of section) { const q = local(p, contourBox); disc(inferredImage, q[0], q[1], 2, amber); }
}

// Record black-pupil component centroids independently from the transform
// anchors.  The 1-2 px left-eye difference is retained as provenance, while
// the established manifest transform remains unchanged for Cubism alignment.
const directPupilCentroids = {
  pupil_left_black_component_centroid: [297.14, 529.50],
  pupil_right_black_component_centroid: [487.55, 507.47],
};
const landmarkMap = Object.fromEntries(guide.anatomical_landmarks.map(p => [p.id, p.source_px]));
landmarkMap.pupil_left = directPupilCentroids.pupil_left_black_component_centroid;
landmarkMap.pupil_right = directPupilCentroids.pupil_right_black_component_centroid;
const landmarkPoints = Object.entries(landmarkMap).map(([id, source_px]) => ({ id, source_px }));
const landmarkBox = bounds(landmarkPoints, 28);
const landmarkImage = localImage(landmarkBox);
for (const p of landmarkPoints) {
  const q = local(p, landmarkBox);
  line(landmarkImage, [q[0] - 12, q[1]], [q[0] + 12, q[1]], 1, magenta, false);
  line(landmarkImage, [q[0], q[1] - 12], [q[0], q[1] + 12], 1, magenta, false);
  disc(landmarkImage, q[0], q[1], 2, magenta);
}

const sourcePng = PNG.sync.read(fs.readFileSync(path.join(referenceDir, 'reference_left_scaled.png')));
const sourceLayer = {
  name: 'REFERENCE__SOURCE_UNROTATED__25PCT__HIDE_BEFORE_EXPORT',
  left: sourceManifest.alignment.raster_layer_position.reference_left[0],
  top: sourceManifest.alignment.raster_layer_position.reference_left[1],
  opacity: 0.25,
  imageData: { width: sourcePng.width, height: sourcePng.height, data: sourcePng.data },
};
const layers = [
  { name: 'GUIDE__VISIBLE_FACE_CONTOUR__CYAN__4PX', left: contourBox.left, top: contourBox.top, opacity: 1, imageData: observedImage },
  { name: 'GUIDE__INFERRED_OCCLUDED__AMBER_DASHED__4PX', left: contourBox.left, top: contourBox.top, opacity: 1, imageData: inferredImage },
  { name: 'GUIDE__LANDMARK_CROSSHAIRS__MAGENTA', left: landmarkBox.left, top: landmarkBox.top, opacity: 1, imageData: landmarkImage },
  sourceLayer,
];
fs.writeFileSync(psdPath, writePsdBuffer({ width: CANVAS[0], height: CANVAS[1], children: layers }));

const read = readPsd(fs.readFileSync(psdPath), { useImageData: true, skipThumbnail: true });
const expected = layers;
const problems = [];
if (read.width !== CANVAS[0] || read.height !== CANVAS[1]) problems.push('canvas dimensions');
if ((read.children || []).length !== expected.length) problems.push('layer count');
for (let i = 0; i < expected.length; i++) {
  const actual = read.children && read.children[i], wanted = expected[i];
  if (!actual || actual.name !== wanted.name) problems.push(`layer ${i} name`);
  if (!actual || actual.left !== wanted.left || actual.top !== wanted.top) problems.push(`layer ${i} position`);
  if (!actual || Math.abs(actual.opacity - wanted.opacity) > 0.01) problems.push(`layer ${i} opacity`);
  if (!actual || !actual.imageData || actual.imageData.width !== wanted.imageData.width || actual.imageData.height !== wanted.imageData.height) problems.push(`layer ${i} dimensions`);
  if (actual && actual.imageData && !Buffer.from(actual.imageData.data).equals(Buffer.from(wanted.imageData.data))) problems.push(`layer ${i} RGBA readback`);
}
const manifest = {
  purpose: 'Transparent source-space contour guide for the left-screen oblique nod endpoint. Hide all guide/reference layers before export.',
  source: { path: sourcePath, sha256: sha256(sourcePath), orientation: 'unrotated supplied source' },
  canvas: CANVAS,
  transform_retained_from_reference_overlay: { scale: SCALE, offset: OFFSET, operation: 'uniform scale and translation only' },
  direct_source_pixel_inspection: {
    black_pupil_component_centroids: directPupilCentroids,
    retained_transform_anchors: sourceManifest.alignment.source_pupil_centres,
    decision: 'No transform correction. Right differs by <=0.3 px; left differs by 1.2 px right and 2.2 px down due to black-fill centroid versus visual eye anchor. Retaining the established transform avoids an unjustified 0.4% rescale.',
  },
  contour_points_source_px: contour,
  landmark_crosshairs_source_px: landmarkPoints,
  layers: layers.map(x => ({ name: x.name, left: x.left, top: x.top, opacity: x.opacity, dimensions: [x.imageData.width, x.imageData.height] })),
  psd_sha256: sha256(psdPath),
};
fs.writeFileSync(guideManifestPath, JSON.stringify(manifest, null, 2) + '\n');
const report = {
  status: problems.length ? 'fail' : 'pass', psd: psdPath, sha256: manifest.psd_sha256,
  canvas: [read.width, read.height], colorMode: read.colorMode, bitsPerChannel: read.bitsPerChannel,
  layers: (read.children || []).map(x => ({ name: x.name, left: x.left, top: x.top, opacity: x.opacity, dimensions: [x.imageData.width, x.imageData.height] })),
  checks: { canvas: !problems.includes('canvas dimensions'), layerCount: !problems.includes('layer count'), namesPositionsOpacityDimensionsAndRgba: !problems.some(x => x.startsWith('layer')) },
  problems,
};
fs.writeFileSync(verificationPath, JSON.stringify(report, null, 2) + '\n');
if (problems.length) throw new Error(problems.join('; '));
process.stdout.write(JSON.stringify(report, null, 2) + '\n');
