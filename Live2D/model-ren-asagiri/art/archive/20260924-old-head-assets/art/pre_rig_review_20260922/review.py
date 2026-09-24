"""Read-only source audit and provisional overlap diagnostics; not rig validation."""
from pathlib import Path
import sys,json,hashlib,shutil,datetime
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;BASE=ROOT/'art/processing_v001'
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
def bg(im):
 b=Image.new('RGBA',im.size,(85,105,110));b.alpha_composite(im);return b.convert('RGB')

prev=json.loads((ROOT/'art/review_remaining_v001/inventory.json').read_text());previous={side:{n['name']:n for n in rows} for side,rows in prev.items()}
inventory={};images={};snap=OUT/'source_snapshot';snap.mkdir(exist_ok=True)
for side in ['front','back']:
 rows=[]
 for p in (BASE/side/'parts').glob('*.png'):
  im=Image.open(p).convert('RGBA');h=hashlib.sha256(p.read_bytes()).hexdigest();old=previous[side].get(p.stem)
  rows.append({'name':p.stem,'size':im.size,'bbox':im.getbbox(),'sha256':h,'updated':datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds'),'changedSincePriorReview':old is None or h!=old['sha256']})
  if side=='front':
   images[p.stem]=im
   if p.stem.startswith(('face','ear','hair','brow','neck','collar','shirt','Upper','FILL','ALT_whole')):
    q=snap/p.name
    if not q.exists():shutil.copy2(p,q)
    assert q.read_bytes()==p.read_bytes()
 inventory[side]=rows
(OUT/'inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')

def sheet(names,filename,cols=3,side='front'):
 dest=Image.new('RGB',(cols*380,((len(names)+cols-1)//cols)*380),(65,75,80));d=ImageDraw.Draw(dest)
 for i,n in enumerate(names):
  im=Image.open(BASE/side/'parts'/(n+'.png')).convert('RGBA');b=im.getbbox();im=im.crop(b) if b else im;tile=bg(im);tile.thumbnail((350,310));x=i%cols*380;y=i//cols*380
  dest.paste(tile,(x+(380-tile.width)//2,y+55));d.text((x+6,y+7),n,font=font,fill='white');d.text((x+6,y+30),str(b),font=font,fill='white')
 dest.save(OUT/(filename+'.jpg'),quality=96)
sheet(['face_underfill','brow_R','brow_L','ear_R','ear_L','ear_R_surface','ear_L_surface','neck-clavicle','shirt_inside','collar_R','collar_L','shirt_torso'],'skin_ears_neck')
sheet([n for n in images if n.startswith('hair')],'hair')
sheet(['FILL_eye_white_R','FILL_eye_white_L','Upper_eyelid_right','Upper_eyelid_left','ALT_eyelash_upper_R','ALT_eyelash_upper_L','ALT_whole_eye_R','ALT_whole_eye_L'],'eyes')
sheet(['upper_arm_R','upper_arm_L','forearm_R','forearm_L','hand_R','hand_L','sleeve_R','sleeve_L','shoe_R','shoe_L'],'body',4)
sheet([r['name'] for r in inventory['back']],'back',4,'back')

old=json.loads((BASE/'front/manifest.json').read_text());pos={q['name']:(q['left'],q['top']) for q in old['layers']}
for q in json.loads((ROOT/'art/review_20260921_repairs/changes.json').read_text()):
 if q['name'].startswith('hair'):
  dx,dy=q.get('estimated_placement_delta',[0,0]);x,y=pos[q['name']];pos[q['name']]=(x+dx,y+dy)
pos.update({'neck-clavicle':(1822,1044),'shirt_inside':(1717,1128),'collar_R':(1725,1150),'collar_L':(1964,1147)})
mouth=json.loads((ROOT/'art/mouth_motion_v002/closed/manifest.json').read_text())
context=Image.new('RGBA',(760,960))
for q in mouth['layers']:
 if q['name'] not in ['face_underfill'] and q['visible']:
  context.alpha_composite(Image.open(ROOT/'art/mouth_motion_v002/closed'/q['path']).convert('RGBA'),(q['left'],q['top']))

def assemble(mode='normal',shift=(0,0)):
 c=Image.new('RGBA',(4000,3000));dx,dy=shift
 def add(n,head=False,extra=(0,0)):
  x,y=pos[n];c.alpha_composite(images[n],(x+(dx if head else 0)+extra[0],y+(dy if head else 0)+extra[1]))
 add('hair_back',True)
 for n in ['shirt_inside','neck-clavicle','shirt_torso','collar_R','collar_L']:add(n)
 for n in ['ear_R','ear_L']:add(n,True)
 add('face_underfill',True)
 if mode!='ears_base_only':
  for n in ['ear_R_surface','ear_L_surface']:add(n,True)
 c.alpha_composite(context,(1620+dx,270+dy))
 for n in ['brow_R','brow_L']:add(n,True)
 if mode not in ['nohair','ears_base_only']:
  for n in ['hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C','hair_ahoge']:
   offset=(0,0)
   if mode=='hair_separation':offset={'hair_front_C':(0,20),'hair_side_R':(-20,0),'hair_side_L':(20,0),'hair_ahoge':(0,-12)}.get(n,(0,0))
   add(n,True,offset)
 return c
for name,mode,shift in [('head_neck_static','normal',(0,0)),('without_front_hair','nohair',(0,0)),('ears_base_only','ears_base_only',(0,0)),('hair_separation_probe','hair_separation',(0,0)),('head_shift_probe','normal',(25,-15))]:
 im=assemble(mode,shift);crop=bg(im.crop((1460,80,2540,1650)));crop.save(OUT/(name+'.jpg'),quality=96)

# Neck/lower shirt close-up and absence of face overlay distinguish real excess from layer order.
neck=Image.new('RGBA',(4000,2000))
for n in ['shirt_inside','neck-clavicle','shirt_torso','collar_R','collar_L']:
 neck.alpha_composite(images[n],pos[n])
bg(neck.crop((1620,990,2370,1680))).save(OUT/'neck_collar_detail.jpg',quality=97)
# Nascent hair-alpha overlap check: expose a contrasting background behind hair only.
hair=Image.new('RGBA',(4000,1600))
for n in ['hair_back','hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C','hair_ahoge']:hair.alpha_composite(images[n],pos[n])
bg(hair.crop((1460,80,2540,1140))).save(OUT/'hair_only.jpg',quality=97)

checks={side:all(hashlib.sha256((BASE/side/'parts'/(r['name']+'.png')).read_bytes()).hexdigest()==r['sha256'] for r in rows) for side,rows in inventory.items()}
assert all(checks.values());(OUT/'source_unchanged.json').write_text(json.dumps(checks),encoding='utf-8')
(OUT/'placements_review.json').write_text(json.dumps({'status':'provisional diagnostic, not approved rig or final registration','positions':pos,'probe':'head +25px X,-15px Y; center bang +20px Y; side hair +-20px X; ahoge -12px Y; not prescribed ranges'},indent=2),encoding='utf-8')
print(json.dumps({'count':{s:len(r) for s,r in inventory.items()},'updatedSincePrior':{s:[r['name'] for r in rows if r['changedSincePriorReview']] for s,rows in inventory.items()},'sourceUnchanged':checks}))
