"""Derive a moderate conversation opening from current expression donors.
Never modifies accepted PNGs. Coordinates remain in the 4000x6000 artwork.
"""
from pathlib import Path
import sys, json, hashlib
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'art/processing_v001/tools/pylib'))
from PIL import Image
import numpy as np
import cv2

SRC=ROOT/'art/head/expression_sources/mouth'
OUT.mkdir(exist_ok=True)
(OUT/'parts').mkdir(exist_ok=True)
ORIGIN=(1880,960); SIZE=(250,180)
Y,X=np.indices((SIZE[1],SIZE[0]),dtype=np.float32)
GX=X+ORIGIN[0]; GY=Y+ORIGIN[1]
sx=(GX-2004)/.66+121
u=np.clip(sx/242,0,1)
anchor=1017+5*np.sin(np.pi*u)-(22+5*np.sin(np.pi*u))
layers=[]; hashes={}

def remap(im, ym):
    ar=np.array(im).astype('float32')/255
    ar[:,:,:3]*=ar[:,:,3:4]
    out=cv2.remap(ar,sx.astype('float32'),ym.astype('float32'),cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    out=np.clip(out,0,1)
    out[:,:,:3]=np.divide(out[:,:,:3],out[:,:,3:4],out=np.zeros_like(out[:,:,:3]),where=out[:,:,3:4]>1e-6)
    return Image.fromarray(np.uint8(np.clip(out,0,1)*255+.5))

for name in ['mouth_cavity','mouth_teeth_upper','mouth_tongue','mouth_rim_upper','mouth_rim_lower']:
    p=SRC/(name+'.png'); im=Image.open(p).convert('RGBA')
    hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    donor=Image.new('RGBA',(250,200)); donor.alpha_composite(im,(16,96) if name=='mouth_rim_lower' else (0,0))
    if name=='mouth_teeth_upper': ym=(GY-anchor)/.52
    elif name.startswith('mouth_rim_'):
        a=np.asarray(donor)[:,:,3].astype(float)
        centers=np.divide((a*np.arange(200)[:,None]).sum(0),a.sum(0),out=np.zeros(250),where=a.sum(0)>0)
        valid=np.where(a.sum(0)>0)[0]
        centers=np.interp(np.arange(250),valid,centers[valid])
        center=np.interp(sx,np.arange(250),centers)
        spans=np.array([np.ptp(np.where(a[:,i]>10)[0]) if np.any(a[:,i]>10) else 0 for i in range(250)])
        keep=np.interp(sx,np.arange(250),np.clip((25-spans)/15,0,1))
        stroke=.42+(.56-.42)*keep
        ym=(GY-(anchor+.42*center))/stroke+center
    else: ym=(GY-anchor)/.42
    result=remap(donor,ym)
    box=result.getbbox(); result.crop(box).save(OUT/'parts'/(name+'.png'))
    layers.append(dict(name=name,path='parts/'+name+'.png',left=ORIGIN[0]+box[0],top=ORIGIN[1]+box[1],visible=True))

manifest={'canvas':{'width':4000,'height':6000},'layers':layers,'output':{'psd':'Ren_mouth_addition.psd','flattenedPng':'mouth_layer_composite.png','previewPng':'mouth_layer_preview.png','verificationJson':'psd_verification.json','previewBackground':'#657078'}}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(OUT/'source_hashes.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
# Review on the current canonical head, omitting its closed-mouth line.
head=json.loads((ROOT/'art/head/assembly.json').read_text(encoding='utf-8'))
origin=(1450,70); comp=Image.new('RGBA',(1110,1170))
for q in head['layers']:
    if q['name']=='mouth_closed': continue
    im=Image.open(ROOT/'art/head'/q['file']).convert('RGBA')
    x,y=q['globalPosition'];comp.alpha_composite(im,(x-origin[0],y-origin[1]))
for q in layers:
    im=Image.open(OUT/q['path']).convert('RGBA');comp.alpha_composite(im,(q['left']-origin[0],q['top']-origin[1]))
bg=Image.new('RGBA',comp.size,'#657078');bg.alpha_composite(comp);bg.convert('RGB').save(OUT/'mouth_on_current_head.jpg',quality=95)
print(json.dumps(layers))
