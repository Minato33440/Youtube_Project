from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
BASE=ROOT/'art/processing_v001/front/parts';OLD=ROOT/'art/pre_rig_review_20260922'
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
names=['hair_front_C','hair_side_L','hair_side_R','hair_front_L','hair_front_R','shirt_torso','eyelash_upper_R_original','eyelash_upper_L_original']
pos=json.loads((OLD/'placements_review.json').read_text())['positions']
oldpos=dict(pos)
if (OUT/'registration.json').exists():
 for n,r in json.loads((OUT/'registration.json').read_text()).items():pos[n]=r['position']
images={p.stem:Image.open(p).convert('RGBA') for p in BASE.glob('*.png')}
prior={x['name']:x for x in json.loads((OLD/'inventory.json').read_text())['front']}
rows=[];snap=OUT/'source_snapshot';snap.mkdir(exist_ok=True)
for n in names:
 p=BASE/(n+'.png');h=hashlib.sha256(p.read_bytes()).hexdigest();im=images[n]
 rows.append(dict(name=n,size=im.size,bbox=im.getbbox(),sha256=h,previous=prior[n],position=pos.get(n)))
 shutil.copy2(p,snap/p.name)
(OUT/'inventory.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
def bg(im):
 b=Image.new('RGBA',im.size,(80,105,110));b.alpha_composite(im);return b.convert('RGB')
def save(im,name,box=None): bg(im.crop(box) if box else im).save(OUT/(name+'.jpg'),quality=96)
sheet=Image.new('RGB',(1200,1200),(65,75,80));d=ImageDraw.Draw(sheet)
for i,n in enumerate(names):
 im=images[n];tile=bg(im);tile.thumbnail((380,335));x=i%3*400;y=i//3*400
 sheet.paste(tile,(x+(400-tile.width)//2,y+60));d.text((x+6,y+5),n,font=font,fill='white');d.text((x+6,y+30),str(im.size),font=font,fill='white')
sheet.save(OUT/'parts.jpg',quality=96)
mouthdir=ROOT/'art/mouth_motion_v002/closed';mouth=json.loads((mouthdir/'manifest.json').read_text())
context=Image.new('RGBA',(760,960))
for q in mouth['layers']:
 if q['visible'] and q['name']!='face_underfill':context.alpha_composite(Image.open(mouthdir/q['path']).convert('RGBA'),(q['left'],q['top']))
hairnames=['hair_back','hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C','hair_ahoge']
def assemble(old=False,probe=False,neck_over=False):
 c=Image.new('RGBA',(4000,3000))
 def add(n,delta=(0,0)):
  im=images[n]
  if old and (OLD/'source_snapshot'/(n+'.png')).exists():im=Image.open(OLD/'source_snapshot'/(n+'.png')).convert('RGBA')
  x,y=(oldpos if old else pos)[n];c.alpha_composite(im,(x+delta[0],y+delta[1]))
 add('hair_back')
 seq=['shirt_inside','neck-clavicle','shirt_torso','collar_R','collar_L']
 if neck_over:seq=['shirt_torso','shirt_inside','neck-clavicle','collar_R','collar_L']
 for n in seq:add(n)
 for n in ['ear_R','ear_L','face_underfill']:add(n)
 c.alpha_composite(context,(1620,270))
 for n in ['brow_R','brow_L']:add(n)
 for n in hairnames[1:]:
  off={'hair_front_C':(0,20),'hair_side_R':(-20,0),'hair_side_L':(20,0),'hair_ahoge':(0,-12)}.get(n,(0,0)) if probe else (0,0)
  add(n,off)
 return c
for n,kw in [('current',{}),('previous',{'old':True}),('probe',{'probe':True}),('neck_over',{'neck_over':True})]:save(assemble(**kw),n,(1460,80,2540,1700))
for n,kw in [('hair_current',{}),('hair_previous',{'old':True})]:save(assemble(**kw),n,(1480,90,2500,1120))
save(assemble(),'collar_current',(1600,980,2400,1720));save(assemble(neck_over=True),'collar_neck_over',(1600,980,2400,1720))
checks={r['name']:hashlib.sha256((BASE/(r['name']+'.png')).read_bytes()).hexdigest()==r['sha256'] for r in rows}
(OUT/'source_unchanged.json').write_text(json.dumps(checks),encoding='utf8');assert all(checks.values())
print(json.dumps([{k:r[k] for k in ['name','size','bbox','position']} for r in rows]))
