from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'art/processing_v001/front'
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
sys.path.insert(0,str(ROOT/'art/processing_v001/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import cv2
from psd_tools import PSDImage
spec=json.loads((BASE/'manifest.json').read_text())['layers']
old={l.name:l.topil().convert('RGBA') for l in PSDImage.open(BASE/'Ren_front_parts_v001.psd')}
new={l['name']:Image.open(BASE/l['path']).convert('RGBA') for l in spec}
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
changes=[]
offsets={}
for l in spec:
 n=l['name']; a=old[n]; b=new[n]
 changed=a.size!=b.size or a.tobytes()!=b.tobytes()
 if not changed:continue
 rec={'name':n,'before':a.size,'after':b.size,'manifest_xy':[l['left'],l['top']]}
 if a.size!=b.size:
  pad=100
  target=Image.new('RGBA',(b.width+pad*2,b.height+pad*2));target.alpha_composite(b,(pad,pad))
  aa=np.array(a); bb=np.array(target)
  mask=(aa[:,:,3]>245).astype('uint8')*255
  score=cv2.matchTemplate(bb[:,:,:3],aa[:,:,:3],cv2.TM_SQDIFF_NORMED,mask=mask)
  score=np.nan_to_num(score,nan=1,posinf=1,neginf=1)
  _,_,loc,_=cv2.minMaxLoc(score)
  offsets[n]=(pad-loc[0],pad-loc[1])
  rec['estimated_placement_delta']=offsets[n];rec['matching_error']=float(score[loc[1],loc[0]])
 changes.append(rec)
def render(mode='normal',correct=False,backup=False):
 im=Image.new('RGBA',(4000,6000))
 for l in spec:
  n=l['name'];v=l['visible']
  if mode=='open':
   if n=='mouth_closed':v=False
   if n.startswith('ALT_mouth_'):v=True
  if mode=='nohair' and n.startswith('hair_'):v=False
  if mode=='neck' and (n.startswith(('hair_','face_','ear_','brow_','eye','iris','mouth'))):v=False
  if not v:continue
  patch=new[n]
  bp=BASE/'parts/buckup'/f'{n}.png'
  if backup and bp.exists():patch=Image.open(bp).convert('RGBA')
  dx,dy=offsets.get(n,(0,0)) if correct and not(backup and bp.exists()) else (0,0)
  im.alpha_composite(patch,(l['left']+dx,l['top']+dy))
 return im
def bg(im,color=(95,95,95,255)):
 x=Image.new('RGBA',im.size,color);x.alpha_composite(im);return x.convert('RGB')
for mode in ['normal','open','nohair','neck']:
 im=render(mode);bg(im.crop((1450,110,2550,1660))).save(OUT/f'{mode}_current.png')
 if mode in ['normal','open']:
  bg(render(mode,True).crop((1450,110,2550,1660))).save(OUT/f'{mode}_aligned_estimate.png')
bg(render().resize((800,1200))).save(OUT/'full_current.jpg')
bg(render('open',backup=True).crop((1810,880,2170,1180)).resize((720,600))).save(OUT/'mouth_backup.png')
bg(render('open').crop((1810,880,2220,1230)).resize((820,700))).save(OUT/'mouth_current.png')
names=[x['name'] for x in changes]
for start in range(0,len(names),8):
 subset=names[start:start+8]; sheet=Image.new('RGB',(1200,360*len(subset)),(75,75,75));draw=ImageDraw.Draw(sheet)
 for row,n in enumerate(subset):
  for col,im in enumerate([old[n],new[n]]):
   tile=bg(im);tile.thumbnail((575,310));sheet.paste(tile,(col*600+(600-tile.width)//2,row*360+42))
   draw.text((col*600+10,row*360+8),f'{n} / {"BEFORE" if col==0 else "CURRENT"} {im.width}x{im.height}',font=font,fill='white')
 sheet.save(OUT/f'parts_{start//8+1}.jpg',quality=95)
(OUT/'changes.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
sheet=Image.new('RGB',(1200,840),(95,95,95));d=ImageDraw.Draw(sheet)
for i,(label,im) in enumerate([
 ('BACKUP: saved mouth layer stack',render('open',backup=True).crop((1875,925,2165,1175))),
 ('CURRENT: existing coordinates, all mouth layers',render('open').crop((1875,925,2220,1210))),
 ('CURRENT interior only / fit preview',new['ALT_mouth_interior']),
 ('CURRENT tongue only',new['ALT_mouth_tongue'])]):
 tile=bg(im);tile.thumbnail((550,350));tile=tile.resize((round(tile.width*min(550/tile.width,350/tile.height)),round(tile.height*min(550/tile.width,350/tile.height))))
 x=(i%2)*600;y=(i//2)*420;sheet.paste(tile,(x+(600-tile.width)//2,y+45));d.text((x+10,y+10),label,font=font,fill='white')
sheet.save(OUT/'mouth_comparison.jpg',quality=96)
# Single mouth replacement preview is for visual judgement only. No part/manifest writes.
# Re-render without the closed mouth; keep all mouth alternatives hidden except fitted interior.
single=Image.new('RGBA',(4000,6000))
for l in spec:
 n=l['name']
 if not l['visible'] or n=='mouth_closed':continue
 dx,dy=offsets.get(n,(0,0));single.alpha_composite(new[n],(l['left']+dx,l['top']+dy))
single.alpha_composite(new['ALT_mouth_interior'].resize((185,149),Image.Resampling.LANCZOS),(1910,959))
bg(single.crop((1630,690,2390,1190))).save(OUT/'mouth_single_fit.png')
# Numbered findings on an estimated-alignment composite; labels map to REVIEW.md.
annot=bg(render('normal',True).crop((1450,110,2550,1660)))
d=ImageDraw.Draw(annot)
for num,box in [(1,(405,155,640,345)),(2,(145,390,460,438)),(3,(305,465,480,570)),(4,(750,665,920,815)),(5,(350,945,790,1250))]:
 d.rectangle(box,outline=(255,85,70),width=3);d.rectangle((box[0],box[1]-27,box[0]+30,box[1]),fill=(175,25,20));d.text((box[0]+7,box[1]-26),str(num),font=font,fill='white')
annot.save(OUT/'findings.png')
targets=['neck','collar_R','collar_L','face_surface','ear_R','ear_R_surface','ear_L','ear_L_surface']
sheet=Image.new('RGB',(1200,400*4),(75,75,75));d=ImageDraw.Draw(sheet)
for i,n in enumerate(targets):
 im=bg(new[n]);im.thumbnail((570,350));x=(i%2)*600;y=(i//2)*400;sheet.paste(im,(x+(600-im.width)//2,y+40));d.text((x+10,y+8),n,font=font,fill='white')
sheet.save(OUT/'neck_face_ears.jpg',quality=96)
print(json.dumps(changes,indent=2))
