from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;BASE=ROOT/'art/processing_v001/front/parts'
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image
import numpy as np
pos=json.loads((ROOT/'art/pre_rig_review_20260922/placements_review.json').read_text())['positions']
for n,r in json.loads((ROOT/'art/overlap_recheck_v002/registration.json').read_text()).items():pos[n]=r['position']
pos['shirt_torso']=[1422,1231]
images={p.stem:Image.open(p).convert('RGBA') for p in BASE.glob('*.png')}
def bg(im):
 b=Image.new('RGBA',im.size,(80,105,110));b.alpha_composite(im);return b.convert('RGB')
# Reuse only the read-only layer assembly section, before the old eyebrows.
s=(ROOT/'art/shirt_brow_recheck_v003/review.py').read_text()
exec(s[s.index("c=Image.new('RGBA',(4000,3000))"):s.index("for n in ['brow_R','brow_L']:add(n)")])
records=[]
for side,xy in [('left',(2070,684)),('right',(1776,687))]:
 n='Upper_eyelid_'+side;im=images[n];c.alpha_composite(im,xy)
 a=np.array(im);pixels=a[:,:,:3][a[:,:,3]>240]
 records.append({'source':n+'.png','role':'eyebrow','provisional_position':xy,'opaque_median_RGB':np.median(pixels,axis=0).tolist(),'sha256':hashlib.sha256((BASE/(n+'.png')).read_bytes()).hexdigest()})
bg(c.crop((1650,610,2350,940))).save(OUT/'brows_closeup.jpg',quality=97)
for n in ['hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C','hair_ahoge']:add(n)
bg(c.crop((1460,80,2540,1700))).save(OUT/'face_with_brows.jpg',quality=97)
(OUT/'placement.json').write_text(json.dumps(records,indent=2),encoding='utf8');print(json.dumps(records))
