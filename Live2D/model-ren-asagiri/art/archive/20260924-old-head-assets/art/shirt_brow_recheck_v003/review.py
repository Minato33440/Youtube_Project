from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;BASE=ROOT/'art/processing_v001/front/parts'
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
old=ROOT/'art/pre_rig_review_20260922';prev=ROOT/'art/overlap_recheck_v002'
pos=json.loads((old/'placements_review.json').read_text())['positions']
for n,r in json.loads((prev/'registration.json').read_text()).items():pos[n]=r['position']
pos['shirt_torso']=[1422,1231] # New canvas adds 25px left/top; verify unchanged cloth below.
names=['shirt_torso','brow_L','brow_R','Upper_eyelid_left','Upper_eyelid_right']
images={p.stem:Image.open(p).convert('RGBA') for p in BASE.glob('*.png')}
snap=OUT/'source_snapshot';snap.mkdir(exist_ok=True);rows=[]
for n in names:
 p=BASE/(n+'.png');shutil.copy2(p,snap/p.name);im=images[n];h=hashlib.sha256(p.read_bytes()).hexdigest()
 before=(prev if n=='shirt_torso' else old)/'source_snapshot'/p.name
 rows.append({'name':n,'size':im.size,'bbox':im.getbbox(),'sha256':h,'changed':hashlib.sha256(before.read_bytes()).hexdigest()!=h,'position':pos.get(n)})
def bg(im):
 b=Image.new('RGBA',im.size,(80,105,110));b.alpha_composite(im);return b.convert('RGB')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
sheet=Image.new('RGB',(1000,700),(80,105,110));d=ImageDraw.Draw(sheet)
for i,n in enumerate(names[1:]):
 tile=bg(images[n]);tile=tile.resize((tile.width*2,tile.height*2));x=i%2*500;y=i//2*350;sheet.paste(tile,(x+10,y+80));d.text((x+10,y+10),n,font=font,fill='white');d.text((x+10,y+40),str(images[n].size),font=font,fill='white')
sheet.save(OUT/'brow_lid_parts.jpg',quality=97)
c=Image.new('RGBA',(4000,3000))
def add(n):c.alpha_composite(images[n],tuple(pos[n]))
for n in ['hair_back','shirt_inside','neck-clavicle','shirt_torso','collar_R','collar_L','ear_R','ear_L','face_underfill']:add(n)
md=ROOT/'art/mouth_motion_v002/closed';m=json.loads((md/'manifest.json').read_text())
for q in m['layers']:
 if q['visible'] and q['name'] not in ['face_underfill','eyes_context']:c.alpha_composite(Image.open(md/q['path']).convert('RGBA'),(1620+q['left'],270+q['top']))
bd=ROOT/'art/blink_assembly_v001/open';b=json.loads((bd/'manifest.json').read_text())
for q in b['layers']:
 if not q['visible'] or q['name']=='face_underfill':continue
 im=Image.open(bd/q['path']).convert('RGBA');x,y=1620+q['left'],270+q['top']
 if q['name'].startswith('upper_lash_'):
  im=images['eyelash_upper_'+q['name'][-1]+'_original'];bb=im.getbbox();x-=bb[0];y-=bb[1]
 c.alpha_composite(im,(x,y))
for n in ['brow_R','brow_L']:add(n)
bg(c.crop((1650,610,2350,940))).save(OUT/'brows_existing_placement.jpg',quality=97)
for n in ['hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C','hair_ahoge']:add(n)
bg(c.crop((1460,80,2540,1700))).save(OUT/'head_shirt.jpg',quality=97)
bg(c.crop((1600,980,2400,1720))).save(OUT/'collar_actual.jpg',quality=97)
# Confirm canvas translation with opaque cloth, excluding the edited neck opening.
import numpy as np
oldshirt=np.array(Image.open(prev/'source_snapshot/shirt_torso.png').convert('RGBA'))
newshirt=np.array(images['shirt_torso'])[25:25+1224,25:25+1102]
cloth_equal=bool(np.array_equal(oldshirt[400:],newshirt[400:]))
valid=(oldshirt[400:,:,3]==255)&(newshirt[400:,:,3]==255)
diff=np.abs(oldshirt[400:,:,:3].astype(float)-newshirt[400:,:,:3].astype(float))[valid]
(OUT/'placement_check.json').write_text(json.dumps({'shirt_position':pos['shirt_torso'],'canvas_offset':[25,25],'lower_cloth_RGBA_exact_match':cloth_equal,'opaque_RGB_mean_difference':float(diff.mean()),'opaque_RGB_max_difference':float(diff.max())}),encoding='utf8')
print('Cloth opaque difference:',diff.mean(),diff.max())
(OUT/'inventory.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
checks={r['name']:hashlib.sha256((BASE/(r['name']+'.png')).read_bytes()).hexdigest()==r['sha256'] for r in rows};assert all(checks.values())
(OUT/'source_unchanged.json').write_text(json.dumps(checks),encoding='utf8');print(json.dumps(rows))
