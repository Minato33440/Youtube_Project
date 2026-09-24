from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont,ImageChops
import numpy as np
PREV=ROOT/'art/face_manual_review_v009';SRC=ROOT/'art/eye_adjust_v007/parts/facial features.png'
sources={}
def load(path):
 sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
 return Image.open(path).convert('RGBA')
sample=load(SRC);shutil.copy2(SRC,OUT/'facial_features_source.png')
audit=json.loads((PREV/'audit.json').read_text())
old=Image.new('RGBA',(850,1134))
for layer in audit['psd_layers']:
 old.alpha_composite(load(PREV/f"layer_{layer['index']:02d}.png"),tuple(layer['bbox'][:2]))
old.save(OUT/'previous_face_reconstructed.png')
assert sample.size==old.size
# Keep the previous registration so added nose shadow cannot shift the new placement.
origin=tuple(audit['registration']['origin'])
alpha_same=np.array_equal(np.array(old)[:,:,3],np.array(sample)[:,:,3])
pos=json.loads((ROOT/'art/pre_rig_review_20260922/placements_review.json').read_text())['positions']
for n,r in json.loads((ROOT/'art/overlap_recheck_v002/registration.json').read_text()).items():pos[n]=r['position']
pos['shirt_torso']=[1422,1231]
context_cache={}
def context(n):
 if n not in context_cache:
  folder='shirt_brow_recheck_v003' if n=='shirt_torso' else 'overlap_recheck_v002' if n in ['hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C'] else 'pre_rig_review_20260922'
  context_cache[n]=load(ROOT/'art'/folder/'source_snapshot'/(n+'.png'))
 return context_cache[n]
def assemble(face):
 c=Image.new('RGBA',(4000,3000))
 for n in ['hair_back','shirt_inside','neck-clavicle','shirt_torso','collar_R','collar_L','ear_R','ear_L']:c.alpha_composite(context(n),tuple(pos[n]))
 c.alpha_composite(face,origin)
 for n in ['hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C','hair_ahoge']:c.alpha_composite(context(n),tuple(pos[n]))
 return c
def bg(im):
 c=Image.new('RGBA',im.size,(80,105,110,255));c.alpha_composite(im);return c.convert('RGB')
raw=load(ROOT/'art_assets/ren-stand-pony-front-4000x6000.png')
newcanvas=assemble(sample);oldcanvas=assemble(old)
box=(1460,80,2540,1600)
v008=load(ROOT/'art/eye_adjust_v008/face_sample.jpg').crop((0,0,1080,1520)).convert('RGB')
panels=[bg(raw.crop(box)),v008,bg(oldcanvas.crop(box)),bg(newcanvas.crop(box))]
for i,panel in enumerate(panels):panel.save(OUT/f'face_{i+1:02d}.png')
labels=['① 原画','② 旧 v008','③ 前回の手修正版','④ 今回：鼻筋の影＋upper_crease']
fontpath=next(p for p in [Path('C:/Windows/Fonts/meiryo.ttc'),Path('C:/Windows/Fonts/YuGothM.ttc')] if p.exists())
def sheet(ims,sz,cols,name,fontsize=23):
 w,h=sz;head=48;rows=(len(ims)+cols-1)//cols;c=Image.new('RGB',(w*cols,(h+head)*rows),(58,63,67));d=ImageDraw.Draw(c);font=ImageFont.truetype(str(fontpath),fontsize)
 for i,im in enumerate(ims):
  x=i%cols*w;y=i//cols*(h+head);c.paste(im.resize(sz,Image.Resampling.LANCZOS),(x,y+head));d.text((x+12,y+8),labels[i],font=font,fill='white')
 c.save(OUT/name,quality=97)
sheet(panels,(540,760),2,'comparison_4_grid.jpg')
sheet(panels,(540,760),4,'comparison_4_horizontal.jpg')
eyebox=(1700,690,2280,1040)
eyes=[bg(raw.crop(eyebox)),v008.crop((240,610,820,960)),bg(oldcanvas.crop(eyebox)),bg(newcanvas.crop(eyebox))]
sheet(eyes,(812,490),2,'eyes_nose_4_grid.jpg',26)
# Quantify agreement with the previous saved contextual preview; JPEG rounding is expected.
prev_saved=load(PREV/'current_with_hair.jpg').convert('RGB')
reconstructed=bg(oldcanvas.crop((1460,240,2540,1600)))
mae=float(np.abs(np.array(prev_saved).astype(float)-np.array(reconstructed).astype(float)).mean())
validation={'source':str(SRC),'sampleSize':sample.size,'globalOrigin':origin,'placement':'Same as v009; no resizing or repositioning of individual facial parts','alphaIdenticalToPreviousReconstructedPSD':bool(alpha_same),'previousReconstructionMeanAbsRGBvsSavedJpeg':mae,'labels':labels,'context':'Same verified old hair/neck/ear snapshots for comparison, not latest nape audit','sourceUnchanged':all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in sources.items()),'sourceHashes':sources}
(OUT/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf8')
assert validation['sourceUnchanged']
print(json.dumps({k:v for k,v in validation.items() if k!='sourceHashes'},ensure_ascii=False,indent=2))
