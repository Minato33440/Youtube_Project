"""Closed-lash transition donors; accepted head PNGs are never changed."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'art/processing_v001/tools/pylib'))
import numpy as np
import cv2
from PIL import Image
layers=[]; hashes={}
for side,left,width in [('L',2066,193),('R',1738,183)]:
    p=ROOT/'art/head/expression_sources/blink'/f'eyelash_upper_{side}_original.png'
    a=np.array(Image.open(p).convert('RGBA')).astype('float32')/255
    hashes[side]=hashlib.sha256(p.read_bytes()).hexdigest()
    # Keep the connected opaque stroke, excluding faint extraction remnants.
    alpha=a[:,:,3]
    n,labels,stats,_=cv2.connectedComponentsWithStats((alpha>.40).astype('uint8'),8)
    keep=1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
    mask=cv2.dilate((labels==keep).astype('uint8'),np.ones((3,3),np.uint8))
    a[:,:,3]*=mask
    yy,xx=np.where(a[:,:,3]>.4)
    box=(xx.min(),yy.min(),xx.max()+1,yy.max()+1)
    a=a[box[1]:box[3],box[0]:box[2]].copy()
    alpha=a[:,:,3]; h,w=alpha.shape
    centers=np.divide((alpha*np.arange(h)[:,None]).sum(0),alpha.sum(0),out=np.zeros(w),where=alpha.sum(0)>0)
    valid=np.where(alpha.sum(0)>0)[0]
    centers=np.interp(np.arange(w),valid,centers[valid])
    Y,X=np.indices((42,width),dtype='float32')
    sx=X*(w-1)/(width-1)
    center=np.interp(sx,np.arange(w),centers)
    curve=10+7*np.sin(np.pi*X/(width-1))
    sy=(Y-curve)/.55+center
    a[:,:,:3]*=a[:,:,3:4]
    b=cv2.remap(a,sx,sy.astype('float32'),cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    b=np.clip(b,0,1)
    b[:,:,:3]=np.divide(b[:,:,:3],b[:,:,3:4],out=np.zeros_like(b[:,:,:3]),where=b[:,:,3:4]>1e-6)
    im=Image.fromarray(np.uint8(np.clip(b,0,1)*255+.5))
    name=f'eyelash_closed_{side}'
    im.save(OUT/'parts'/f'{name}.png')
    layers.append(dict(name=name,path=f'parts/{name}.png',left=left,top=818,visible=True))
manifest={'canvas':{'width':4000,'height':6000},'layers':layers,'output':{'psd':'Ren_blink_transition.psd','flattenedPng':'blink_layer_composite.png','previewPng':'blink_layer_preview.png','verificationJson':'blink_psd_verification.json','previewBackground':'#657078'}}
(OUT/'blink_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(OUT/'blink_source_hashes.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
print(json.dumps(layers))
