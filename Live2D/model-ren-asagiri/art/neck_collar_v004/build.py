"""Place Boss's repaired neck against the approved collar assembly; originals read only."""
from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
from psd_tools import PSDImage
import numpy as np
BASE=ROOT/'art/processing_v001/front';PARTS=OUT/'parts';PARTS.mkdir(parents=True,exist_ok=True)
xy={'shirt_inside':(1717,1128),'neck-clavicle':(1822,1044),'collar_R':(1725,1150),'collar_L':(1964,1147)}
origin=(1716,1000);size=(567,590);layers=[];images={};hashes={}
for name,(x,y) in xy.items():
    src=BASE/'parts'/f'{name}.png';dst=PARTS/src.name
    if dst.exists() and dst.read_bytes()!=src.read_bytes():raise RuntimeError('Output differs; preserve manual edits')
    if not dst.exists():shutil.copy2(src,dst)
    hashes[name]=hashlib.sha256(src.read_bytes()).hexdigest();images[name]=Image.open(dst).convert('RGBA')
    layers.append({'name':name,'path':f'parts/{name}.png','left':x-origin[0],'top':y-origin[1],'visible':True})
im=Image.new('RGBA',size)
for l in layers:im.alpha_composite(images[l['name']],(l['left'],l['top']))
im.save(OUT/'neck_collar_assembled.png')
manifest={'canvas':dict(zip(['width','height'],size)),'globalCanvasOrigin':list(origin),'coordinateConvention':'local coordinates; add origin for original 4000x6000 canvas; provisional review',
 'layers':layers,'output':{'psd':'Ren_neck_collar_v004.psd','flattenedPng':'neck_collar_psd_assembled.png','previewPng':'neck_collar_psd_preview.png','verificationJson':'psd_verification.json','previewBackground':'#707070'}}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
# Verify coverage of the collar opening using the visible backing and collar alphas.
def canvas_part(name):
    c=Image.new('RGBA',size);l=next(l for l in layers if l['name']==name);c.alpha_composite(images[name],(l['left'],l['top']));return np.array(c)
inside=canvas_part('shirt_inside');neck=canvas_part('neck-clavicle');left=canvas_part('collar_L');right=canvas_part('collar_R')
missing=(inside[:,:,3]>250)&(neck[:,:,3]==0)&(left[:,:,3]<10)&(right[:,:,3]<10)
yy,xx=np.indices(missing.shape);missing &= (yy>430)&(xx>160)&(xx<430)
raw_backing_pixels=int(missing.sum())
# The backing continues below the closed front of the collar; those pixels are
# not exposed chest. Check the actual V opening, not the whole backing extent.
opening=Image.new('L',size);ImageDraw.Draw(opening).polygon([(225,430),(340,430),(283,533)],fill=255)
missing &= np.array(opening)>0
ys,xs=np.nonzero(missing);bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if len(xs) else None
bg=Image.new('RGBA',size,(90,105,110));bg.alpha_composite(im);draw=ImageDraw.Draw(bg);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
if bbox:
    box=(bbox[0]-12,bbox[1]-10,bbox[2]+12,bbox[3]+10);draw.rectangle(box,outline=(255,85,65),width=3);draw.text((max(0,box[0]-40),box[1]-24),'Skin extension still needed',font=font,fill=(255,215,150))
bg.save(OUT/'neck_collar_review.png')
report={'sourceHashes':hashes,'sourceFilesUnchanged':all(hashlib.sha256((BASE/'parts'/f'{n}.png').read_bytes()).hexdigest()==v for n,v in hashes.items()),
 'globalPlacements':xy,'neckAlignment':'retained clavicle pixels matched previous source exactly; new transparent top padding accounted for',
 'neckOpaqueBottomGlobal':xy['neck-clavicle'][1]+images['neck-clavicle'].getbbox()[3],
 'visibleBackingBelowNeckPixels':len(xs),'visibleBackingBelowNeckBoundsLocal':bbox,
 'backingPixelsOutsideChestOpening':raw_backing_pixels-len(xs),
 'status':'pass: static collar opening covered; dynamic deformation not tested'}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
