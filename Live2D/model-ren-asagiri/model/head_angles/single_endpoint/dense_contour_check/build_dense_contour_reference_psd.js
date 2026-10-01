'use strict';

// Writes an isolated 4000x6000 Cubism reference PSD from the dense source audit.
// It reads existing fixed reference data but does not change it, the source art,
// or any cmo3/model3/runtime artifact.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { PNG } = require(path.resolve(__dirname, '../../../../../../output/live2d/risa_parts_v1/tools/node_modules/pngjs'));
const { readPsd, writePsdBuffer, initializeCanvas } = require(path.resolve(__dirname, '../../../../../../output/live2d/risa_parts_v1/tools/node_modules/ag-psd'));
function imageData(width, height) { return { width, height, data: new Uint8ClampedArray(width * height * 4) }; }
initializeCanvas(() => ({ getContext: () => ({ createImageData: imageData }) }), undefined, imageData);

const out = __dirname;
const singleEndpoint = path.resolve(out, '..');
const referenceDir = path.resolve(out, '../..', 'reference_overlay');
const sourceGuidePath = path.resolve(singleEndpoint, 'guide', 'looking_down_2_source_landmark_guide.json');
const dense = JSON.parse(fs.readFileSync(path.join(out, 'dense_visible_contour_target.json'), 'utf8'));
const sourceGuide = JSON.parse(fs.readFileSync(sourceGuidePath, 'utf8'));
const reference = JSON.parse(fs.readFileSync(path.join(referenceDir, 'reference_overlay_manifest.json'), 'utf8'));
const psdPath = path.join(out, 'dense_contour_reference_4000x6000.psd');
const manifestPath = path.join(out, 'dense_contour_reference_psd_manifest.json');
const reportPath = path.join(out, 'dense_contour_reference_psd_readback.json');
const CANVAS = [4000, 6000];
const SCALE = dense.fixed_reference_transform.full_canvas_scale;
const OFFSET = dense.fixed_reference_transform.full_canvas_offset;
const sha256 = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if (sha256(dense.source.path) !== dense.source.sha256 || dense.source.sha256 !== reference.source.sha256) throw new Error('Source hash mismatch; stop before producing a misleading guide.');
if (SCALE !== reference.alignment.full_canvas_scale || OFFSET[0] !== reference.alignment.full_canvas_offset[0] || OFFSET[1] !== reference.alignment.full_canvas_offset[1]) throw new Error('Dense audit transform differs from fixed reference transform.');
const sourceToCanvas = p => [OFFSET[0] + p[0] * SCALE, OFFSET[1] + p[1] * SCALE];

function set(image, x, y, c) { if (x < 0 || y < 0 || x >= image.width || y >= image.height) return; const i = (Math.round(y) * image.width + Math.round(x)) * 4; image.data.set(c, i); }
function disc(image, x, y, radius, c) { for (let yy = Math.floor(y-radius); yy <= Math.ceil(y+radius); yy++) for (let xx = Math.floor(x-radius); xx <= Math.ceil(x+radius); xx++) if ((xx-x)**2 + (yy-y)**2 <= radius**2) set(image, xx, yy, c); }
function segment(image, a, b, radius, c, dashed) { const dx=b[0]-a[0], dy=b[1]-a[1], n=Math.max(1,Math.ceil(Math.hypot(dx,dy))); for(let i=0;i<=n;i++){ if(dashed && i%24>=14)continue; disc(image,a[0]+dx*i/n,a[1]+dy*i/n,radius,c); } }
function bounds(points, pad) { const xy=points.map(sourceToCanvas); return { left: Math.floor(Math.min(...xy.map(p=>p[0]))-pad), top: Math.floor(Math.min(...xy.map(p=>p[1]))-pad), right: Math.ceil(Math.max(...xy.map(p=>p[0]))+pad), bottom: Math.ceil(Math.max(...xy.map(p=>p[1]))+pad) }; }
function makeLineLayer(name, paths, color, dashed, pad=24) {
  const all=paths.flat(); const b=bounds(all,pad); const im=imageData(b.right-b.left+1,b.bottom-b.top+1);
  for (const pathPoints of paths) { const xy=pathPoints.map(p=>{const q=sourceToCanvas(p);return[q[0]-b.left,q[1]-b.top];}); for(let i=1;i<xy.length;i++)segment(im,xy[i-1],xy[i],2,color,dashed); for(const q of xy)disc(im,q[0],q[1],dashed?2:2.5,color); }
  return {name,left:b.left,top:b.top,opacity:1,imageData:im};
}

const visible = dense.visible_controls_source_px;
const inferred = [dense.inferred_hair_occluded_source_px.right, dense.inferred_hair_occluded_source_px.left];
const cyan = [0,229,255,255], amber = [255,178,46,255], magenta = [255,68,210,255];
const visibleLayer = makeLineLayer('GUIDE__DENSE_VISIBLE_FACE_CONTOUR__CYAN__4PX',[visible],cyan,false);
const inferredLayer = makeLineLayer('GUIDE__DENSE_INFERRED_HAIR_OCCLUDED__AMBER_DASHED__4PX',inferred,amber,true);

const landmarks = sourceGuide.anatomical_landmarks.map(x => ({id:x.id,source_px:x.source_px}));
const landmarkBounds=bounds(landmarks.map(x=>x.source_px),28); const landmarkImage=imageData(landmarkBounds.right-landmarkBounds.left+1,landmarkBounds.bottom-landmarkBounds.top+1);
for(const landmark of landmarks){const p=sourceToCanvas(landmark.source_px), x=p[0]-landmarkBounds.left,y=p[1]-landmarkBounds.top; segment(landmarkImage,[x-12,y],[x+12,y],1,magenta,false);segment(landmarkImage,[x,y-12],[x,y+12],1,magenta,false);disc(landmarkImage,x,y,2,magenta);}
const landmarkLayer={name:'GUIDE__LANDMARK_CROSSHAIRS__MAGENTA',left:landmarkBounds.left,top:landmarkBounds.top,opacity:1,imageData:landmarkImage};

const sourcePng=PNG.sync.read(fs.readFileSync(path.join(referenceDir,'reference_left_scaled.png')));
const sourceLayer={name:'REFERENCE__SOURCE_UNROTATED__25PCT__HIDE_BEFORE_EXPORT',left:reference.alignment.raster_layer_position.reference_left[0],top:reference.alignment.raster_layer_position.reference_left[1],opacity:.25,imageData:{width:sourcePng.width,height:sourcePng.height,data:sourcePng.data}};
const layers=[visibleLayer,inferredLayer,landmarkLayer,sourceLayer];
fs.writeFileSync(psdPath,writePsdBuffer({width:CANVAS[0],height:CANVAS[1],children:layers}));

const read=readPsd(fs.readFileSync(psdPath),{useImageData:true,skipThumbnail:true}); const problems=[];
if(read.width!==CANVAS[0]||read.height!==CANVAS[1])problems.push('canvas dimensions'); if((read.children||[]).length!==layers.length)problems.push('layer count');
for(let i=0;i<layers.length;i++){const a=read.children&&read.children[i],e=layers[i];if(!a||a.name!==e.name)problems.push(`layer ${i} name`);if(!a||a.left!==e.left||a.top!==e.top)problems.push(`layer ${i} position`);if(!a||Math.abs(a.opacity-e.opacity)>.01)problems.push(`layer ${i} opacity`);if(!a||!a.imageData||a.imageData.width!==e.imageData.width||a.imageData.height!==e.imageData.height)problems.push(`layer ${i} dimensions`);if(a&&a.imageData&&!Buffer.from(a.imageData.data).equals(Buffer.from(e.imageData.data)))problems.push(`layer ${i} RGBA readback`);}
const manifest={purpose:'Dense visible-contour reference for Cubism mesh adjustment. Hide every guide/reference layer before export.',source:{path:dense.source.path,sha256:sha256(dense.source.path),orientation:'unrotated supplied source'},canvas:CANVAS,transform:{full_canvas_scale:SCALE,full_canvas_offset:OFFSET,operation:'uniform scale and translation only'},classification:dense.classification,layers:layers.map(x=>({name:x.name,left:x.left,top:x.top,opacity:x.opacity,dimensions:[x.imageData.width,x.imageData.height]})),psd_sha256:sha256(psdPath)};
fs.writeFileSync(manifestPath,JSON.stringify(manifest,null,2)+'\n');
const report={status:problems.length?'fail':'pass',psd:psdPath,sha256:manifest.psd_sha256,canvas:[read.width,read.height],colorMode:read.colorMode,bitsPerChannel:read.bitsPerChannel,layers:(read.children||[]).map(x=>({name:x.name,left:x.left,top:x.top,opacity:x.opacity,dimensions:[x.imageData.width,x.imageData.height]})),checks:{canvas:!problems.includes('canvas dimensions'),layerCount:!problems.includes('layer count'),namesPositionsOpacityDimensionsAndRgba:!problems.some(x=>x.startsWith('layer'))},problems};
fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n'); if(problems.length)throw new Error(problems.join('; ')); process.stdout.write(JSON.stringify(report,null,2)+'\n');
