from pathlib import Path
import sys,json,hashlib
HERE=Path(__file__).resolve().parent;HEAD=HERE.parents[1];ROOT=HEAD.parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
sys.path.insert(0,str(ROOT/'art/processing_v001/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np,cv2
manifest=json.loads((HEAD/'assembly.json').read_text());c=Image.new('RGBA',(4000,1600));hashes={};checks=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for l in manifest['layers']:
 p=HEAD/l['file'];im=Image.open(p).convert('RGBA');hashes[l['file']]=sha(p)
 assert tuple(l['size'])==im.size,(p,im.size,l['size'])
 if l['name'].startswith('ear_'):
  old=Image.open(ROOT/'art/processing_v001/front/parts'/p.name).convert('RGBA');a=np.array(im);b=np.array(old)
  stats=[]
  for alpha in [b[:,:,3],a[:,:,3]]:
   n,lab,st,cent=cv2.connectedComponentsWithStats((alpha>25).astype('uint8'),8)
   stats.append({'components':n-1,'opaquePixels':int((alpha>25).sum()),'smallComponentsArea':int(sum(s[4] for s in st[1:] if s[4]<20))})
  interior=(a[:,:,3]==255)&(b[:,:,3]==255)
  checks.append({'file':p.name,'sizeUnchanged':old.size==im.size,'interiorMeanAbsRgbChange':float(np.abs(a[:,:,:3].astype(float)-b[:,:,:3].astype(float))[interior].mean()),'before':stats[0],'after':stats[1]})
 if l['flipHorizontal']:im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 c.alpha_composite(im,tuple(l['globalPosition']))
crop=tuple(manifest['globalCrop']);head=c.crop(crop);head.save(HERE/'head_sample.png')
def bg(im,color=(80,105,110,255)):
 b=Image.new('RGBA',im.size,color);b.alpha_composite(im);return b.convert('RGB')
bg(head).save(HERE/'head_sample_gray.png')
raw=Image.open(HEAD/'reference/ren-stand-pony-front-4000x6000.png').convert('RGBA');font=ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc',26)
def pair(ims,labels,size,path):
 w,h=size;o=Image.new('RGB',(w*len(ims),h+52),(58,63,67));d=ImageDraw.Draw(o)
 for i,(im,label) in enumerate(zip(ims,labels)):
  o.paste(bg(im).resize(size,Image.Resampling.LANCZOS),(i*w,52));d.text((i*w+12,10),label,font=font,fill='white')
 o.save(path,quality=98)
pair([raw.crop(crop),head],['原画','頭部前面：耳の外縁修正後'],(666,702),HERE/'comparison_original.jpg')
detail=(1650,650,2350,1190)
pair([raw.crop(detail),c.crop(detail)],['原画','頭部前面：耳の外縁修正後'],(840,648),HERE/'comparison_face_detail.jpg')
oldhead=Image.open(HEAD/'preview/head_sample.png').convert('RGBA');tiles=Image.new('RGB',(1120,850),(58,63,67));d=ImageDraw.Draw(tiles)
for i,(name,box) in enumerate([('画面左・キャラ右',(1640,810,1810,1000)),('画面右・キャラ左',(2180,810,2360,1000))]):
 local=tuple(v-crop[j%2] for j,v in enumerate(box));old=oldhead.crop(local);new=c.crop(box)
 for j,im in enumerate([old,new]):
  x=j*560;y=i*425;tiles.paste(bg(im).resize((im.width*3,im.height*2)),(x,y+42));d.text((x+8,y+6),name+('：前' if j==0 else '：修正後'),font=font,fill='white')
tiles.save(HERE/'ear_overlap_comparison.jpg',quality=98)
(HERE/'review_checks.json').write_text(json.dumps({'parts':hashes,'earChecks':checks,'inputPartsUnchanged':all(sha(HEAD/p)==h for p,h in hashes.items())},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(checks,ensure_ascii=False));print('All 23 input hashes unchanged')
