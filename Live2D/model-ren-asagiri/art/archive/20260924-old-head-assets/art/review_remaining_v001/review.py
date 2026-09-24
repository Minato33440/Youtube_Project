from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;BASE=ROOT/'art/processing_v001'
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
from psd_tools import PSDImage
import numpy as np
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
def bg(im):
 c=Image.new('RGBA',im.size,(95,110,115));c.alpha_composite(im);return c.convert('RGB')
def sheet(names,folder,name,cols=3):
 c=Image.new('RGB',(cols*370,((len(names)+cols-1)//cols)*380),(65,75,80));d=ImageDraw.Draw(c)
 for i,n in enumerate(names):
  im=Image.open(folder/f'{n}.png').convert('RGBA');x=i%cols*370;y=i//cols*380
  b=im.getbbox();tile=bg(im.crop(b) if b else im);tile.thumbnail((350,335))
  c.paste(tile,(x+(370-tile.width)//2,y+40));d.text((x+5,y+5),f'{n} {im.width}x{im.height}',font=font,fill='white')
 c.save(OUT/f'{name}.jpg',quality=96)
p=BASE/'front/parts';names=[f.stem for f in p.glob('*.png')]
sheet([n for n in names if n.startswith(('face','ear'))],p,'face_ears')
sheet([n for n in names if n.startswith('hair')],p,'hair')
sheet([n for n in names if n.startswith(('eye','iris','brow','FILL'))],p,'eyes')
sheet([n for n in names if n.startswith(('ALT_eye','ALT_iris','ALT_whole'))],p,'eye_alternatives')
sheet([n for n in names if n.startswith(('upper_arm','forearm','hand','sleeve','shirt_torso','belt','trousers','shoe'))],p,'body',4)
q=BASE/'back/parts';sheet([f.stem for f in q.glob('*.png')],q,'back',4)
old_offsets=json.loads((ROOT/'art/review_20260921_repairs/changes.json').read_text())
offsets={r['name']:r.get('estimated_placement_delta',[0,0]) for r in old_offsets}
spec=json.loads((BASE/'front/manifest.json').read_text())['layers']
for mode in ['head','nohair','face_only']:
 c=Image.new('RGBA',(4000,2000))
 for l in spec:
  n=l['name']
  if not l['visible'] or n in ['neck','collar_L','collar_R']:continue
  if mode=='nohair' and n.startswith('hair'):continue
  if mode=='face_only' and not n.startswith(('face','ear')):continue
  if not n.startswith(('face','ear','hair','eye','iris','brow','mouth_closed')):continue
  im=Image.open(p/f'{n}.png').convert('RGBA');dx,dy=offsets.get(n,[0,0]);c.alpha_composite(im,(l['left']+dx,l['top']+dy))
 bg(c.crop((1480,110,2510,1230))).save(OUT/f'{mode}.png')
audit={}
for side in ['front','back']:
 old={l.name:l for l in PSDImage.open(BASE/side/f'Ren_{side}_parts_v001.psd')};records=[]
 for f in (BASE/side/'parts').glob('*.png'):
  im=Image.open(f).convert('RGBA');oldim=old[f.stem].topil().convert('RGBA') if f.stem in old else None
  records.append({'name':f.stem,'size':im.size,'bbox':im.getbbox(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'sameAsInitialPsd':oldim is not None and oldim.size==im.size and oldim.tobytes()==im.tobytes()})
 audit[side]=records
(OUT/'inventory.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
print({k:len(v) for k,v in audit.items()})
