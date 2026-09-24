"""Reassemble the three corrected collar assets using Boss's overlap sample."""
from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
sys.path.insert(0,str(ROOT/'art/processing_v001/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import cv2
BASE=ROOT/'art/processing_v001/front/parts'
SAMPLE=Path(r'C:\Users\Setona\Pictures\Screenshots\スクリーンショット 2026-09-21 203304.png')
PARTS=OUT/'parts';PARTS.mkdir(parents=True,exist_ok=True)
names=['shirt_inside','collar_R','collar_L'];xy={'shirt_inside':(1,0),'collar_R':(9,22),'collar_L':(248,19)}
hashes={};imgs={}
for name in names:
    src=BASE/f'{name}.png';dst=PARTS/src.name
    if dst.exists() and dst.read_bytes()!=src.read_bytes():raise RuntimeError('Output already differs from source; preserve manual edits: '+str(dst))
    if not dst.exists():shutil.copy2(src,dst)
    hashes[name]=hashlib.sha256(src.read_bytes()).hexdigest();imgs[name]=Image.open(dst).convert('RGBA')
canvas=(567,454)
assembled=Image.new('RGBA',canvas)
for n in names:assembled.alpha_composite(imgs[n],xy[n])
assembled.save(OUT/'collar_assembled.png')
# Keep original complete PNG canvases; outside-canvas pixels must all be transparent.
for n in names:
    a=np.array(imgs[n]);ys,xs=np.nonzero(a[:,:,3]);x,y=xy[n]
    assert xs.min()+x>=0 and ys.min()+y>=0 and xs.max()+x<canvas[0] and ys.max()+y<canvas[1],n
manifest={'canvas':{'width':canvas[0],'height':canvas[1]},'coordinateConvention':'sample-local; pixel top-left; character L is screen right',
 'layers':[{'name':n,'path':f'parts/{n}.png','left':xy[n][0],'top':xy[n][1],'visible':True} for n in names],
 'output':{'psd':'Ren_collar_assembly_v002.psd','flattenedPng':'collar_psd_assembled.png','previewPng':'collar_psd_preview.png','verificationJson':'psd_verification.json','previewBackground':'#707070'}}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
# The screenshot is 1px shorter than the material canvas. Compare only its opaque visible pixels.
sample=Image.open(SAMPLE).convert('RGB');a=np.array(assembled)[:sample.height,:sample.width];b=np.array(sample)
mask=cv2.erode((a[:,:,3]==255).astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)
diff=np.abs(a[:,:,:3].astype(float)-b.astype(float)); report={'sources':hashes,'sourceSample':str(SAMPLE),'sampleSize':sample.size,'canvas':canvas,'positions':xy,
 'sourcePixelsPreserved':True,'outsideCanvasVisiblePixels':0,'opaqueSampleComparison':{'pixels':int(mask.sum()),'meanChannelDifference':float(diff[mask].mean()),'p95ChannelDifference':float(np.percentile(diff[mask],95))},
 'notes':['PNG canvases and RGBA unchanged','Sample has checkerboard; transparency not inferred from screenshot','Sample is 567x453; output retains 567x454 so bottom alpha is not clipped','Local part assembly only; global PSD and cmo3 untouched']}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
sheet=Image.new('RGB',(1164,506),(70,75,80));sheet.paste(sample,(10,42));bg=Image.new('RGBA',canvas,(112,112,112));bg.alpha_composite(assembled);sheet.paste(bg.convert('RGB'),(587,42))
d=ImageDraw.Draw(sheet);d.text((10,10),'BOSS SAMPLE',font=font,fill='white');d.text((587,10),'REASSEMBLED / 3 independent layers',font=font,fill='white');sheet.save(OUT/'collar_comparison.jpg',quality=97)
assert all(hashlib.sha256((BASE/f'{n}.png').read_bytes()).hexdigest()==hashes[n] for n in names)
print(json.dumps(report,indent=2))
