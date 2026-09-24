from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;BASE=ROOT/'art/processing_v001/front'
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
names=['face_underfill','Upper_eyelid_left','Upper_eyelid_right'];snap=OUT/'source_snapshot';snap.mkdir(exist_ok=True)
hashes={};parts={}
for n in names:
 p=BASE/'parts'/f'{n}.png';q=snap/p.name
 if not q.exists():shutil.copy2(p,q)
 assert q.read_bytes()==p.read_bytes(),'Source changed since snapshot'
 hashes[n]=hashlib.sha256(p.read_bytes()).hexdigest();parts[n]=Image.open(q).convert('RGBA')
src=Image.open(ROOT/'art_assets/ren-stand-pony-front-4000x6000.png').convert('RGBA')
positions={'face_underfill':(1697,303),'Upper_eyelid_left':(2061,748),'Upper_eyelid_right':(1767,749)}
over=src.copy()
for n in names[1:]:over.alpha_composite(parts[n],positions[n])
# Original eye pieces are for position checking, not a finished blink-ready eye.
test=Image.new('RGBA',(4000,2000));test.alpha_composite(parts['face_underfill'],positions['face_underfill'])
spec=json.loads((BASE/'manifest.json').read_text())['layers']
for l in spec:
 if l['name'].startswith(('eye_white','iris_','eyelash_upper','brow_')) and l['visible']:
  test.alpha_composite(Image.open(BASE/l['path']).convert('RGBA'),(l['left'],l['top']))
for n in names[1:]:test.alpha_composite(parts[n],positions[n])
def bg(im):
 b=Image.new('RGBA',im.size,(85,105,110));b.alpha_composite(im);return b.convert('RGB')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21)
sheet=Image.new('RGB',(1360,1215),(65,75,80));d=ImageDraw.Draw(sheet)
roi=(1690,705,2310,880)
for i,(label,im) in enumerate([('ORIGINAL artwork',src),('NEW eyelids over original / position check',over),('NEW skin + original eye pieces + NEW eyelids',test)]):
 tile=bg(im.crop(roi)).resize((1240,350))
 sheet.paste(tile,(60,i*405+45));d.text((25,i*405+10),label,font=font,fill='white')
sheet.save(OUT/'eyelid_placement_comparison.jpg',quality=97)
bg(test.crop((1640,280,2350,1210))).save(OUT/'face_with_eyes.png')
im=bg(parts['face_underfill']);d=ImageDraw.Draw(im)
for number,box in [(1,(25,365,580,580)),(2,(175,650,415,765))]:
 d.rectangle(box,outline=(255,90,70),width=2);d.text((box[0]+5,box[1]+5),str(number),font=font,fill=(180,50,20))
im.save(OUT/'face_notes.png')
data={'canvas':[4000,6000],'positions':{n:{'left':xy[0],'top':xy[1],'size':parts[n].size} for n,xy in positions.items()},
 'sideConvention':'left=character L/screen right/blue; right=character R/screen left/brown',
 'status':'review placement; original manifest and PSD not changed','sourceHashes':hashes,
 'sourceFilesUnchanged':all(hashlib.sha256((BASE/'parts'/f'{n}.png').read_bytes()).hexdigest()==h for n,h in hashes.items())}
(OUT/'positions_review.json').write_text(json.dumps(data,indent=2),encoding='utf-8');print(json.dumps(data,indent=2))
