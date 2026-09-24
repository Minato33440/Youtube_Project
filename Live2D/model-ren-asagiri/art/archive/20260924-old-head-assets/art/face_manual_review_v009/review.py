from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
sys.path.insert(0,str(ROOT/'art/processing_v001/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import cv2
from psd_tools import PSDImage
P=ROOT/'art/eye_adjust_v007/parts'
hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in P.glob('*') if f.is_file()}
sample=Image.open(P/'facial features.png').convert('RGBA')
raw=Image.open(ROOT/'art_assets/ren-stand-pony-front-4000x6000.png').convert('RGBA')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
def bg(im,color=(80,105,110)):
 c=Image.new('RGBA',im.size,color+(255,));c.alpha_composite(im);return c.convert('RGB')
def sheet(images,labels,path,sz):
 c=Image.new('RGB',(sz[0]*len(images),sz[1]+44),(65,65,65));d=ImageDraw.Draw(c)
 for i,(im,label) in enumerate(zip(images,labels)):
  c.paste(im.resize(sz,Image.Resampling.LANCZOS),(i*sz[0],44));d.text((i*sz[0]+12,8),label,font=font,fill='white')
 c.save(OUT/path,quality=97)
# Translation only, anchored to the retained nose texture; no independent facial resizing.
box=(405,716,445,780);patch=np.array(sample.crop(box).convert('RGB'))
searchbox=(1920,840,2070,1030);search=np.array(raw.crop(searchbox).convert('RGB'))
res=cv2.matchTemplate(search,patch,cv2.TM_CCOEFF_NORMED);_,score,_,loc=cv2.minMaxLoc(res)
origin=(searchbox[0]+loc[0]-box[0],searchbox[1]+loc[1]-box[1])
print('Nose registration:',origin,score)
pos=json.loads((ROOT/'art/pre_rig_review_20260922/placements_review.json').read_text())['positions']
for n,r in json.loads((ROOT/'art/overlap_recheck_v002/registration.json').read_text()).items():pos[n]=r['position']
pos['shirt_torso']=[1422,1231]
def context(n):
 folder='shirt_brow_recheck_v003' if n=='shirt_torso' else 'overlap_recheck_v002' if n in ['hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C'] else 'pre_rig_review_20260922'
 return Image.open(ROOT/'art'/folder/'source_snapshot'/(n+'.png')).convert('RGBA')
c=Image.new('RGBA',(4000,3000))
for n in ['hair_back','shirt_inside','neck-clavicle','shirt_torso','collar_R','collar_L','ear_R','ear_L']:c.alpha_composite(context(n),tuple(pos[n]))
c.alpha_composite(sample,origin)
for n in ['hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C','hair_ahoge']:c.alpha_composite(context(n),tuple(pos[n]))
crop=(1460,240,2540,1600)
current=bg(c.crop(crop));current.save(OUT/'current_with_hair.jpg',quality=97)
prior=Image.open(ROOT/'art/eye_adjust_v008/face_sample.jpg').crop((0,160,1080,1520))
sheet([bg(raw.crop(crop)),prior,current],['Original','Previous v008','Manual revision'],'comparison.jpg',(540,680))
eyes=(1700,690,2280,930)
sheet([bg(raw.crop(eyes)),bg(c.crop(eyes))],['Original - same scale','Manual - same scale'],'eyes_detail.jpg',(1160,480))
sheet([bg(raw.crop((1700,920,2300,1210))),bg(c.crop((1700,920,2300,1210)))],['Original','Manual revision'],'contour_detail.jpg',(900,435))
psd=PSDImage.open(P/'facial features.psd')
meta=[]
for i,l in enumerate(psd):
 im=l.composite()
 if im is None:continue
 im.save(OUT/f'layer_{i:02d}.png')
 meta.append({'index':i,'name':l.name,'bbox':list(l.bbox),'size':im.size})
active=['face_underfill','ALT_eyelash_upper_L','ALT_eyelash_upper_R','ALT_iris_L_blue','ALT_iris_R_brown','brow_L','brow_R','FILL_eye_white_L','FILL_eye_white_R','lower_eyelid_left','lower_eyelid_right','mouth_closed']
stats=[]
tiles=Image.new('RGB',(1200,420*6),(65,65,65));d=ImageDraw.Draw(tiles)
for i,n in enumerate(active):
 im=Image.open(P/(n+'.png')).convert('RGBA');a=np.array(im)[:,:,3]
 count,lab,s,cent=cv2.connectedComponentsWithStats((a>25).astype('uint8'),8)
 comps=sorted([{'bbox':list(map(int,q[:4])),'area':int(q[4])} for q in s[1:]],key=lambda x:x['area'],reverse=True)
 stats.append({'name':n,'size':list(im.size),'alpha_bbox':im.getbbox(),'components_gt25':comps[:20]})
 preview=bg(im);preview.thumbnail((570,365),Image.Resampling.LANCZOS)
 if im.width<250:preview=bg(im).resize((im.width*2,im.height*2),Image.Resampling.NEAREST)
 x=(i%2)*600;y=(i//2)*420;tiles.paste(preview,(x+15,y+45));d.text((x+12,y+8),n,font=font,fill='white')
tiles.save(OUT/'parts_sheet.jpg',quality=97)
report={'registration':{'origin':origin,'nose_texture_score':score,'method':'Translation only, nose texture, original image; context hair is previous verified snapshot'},'psd_layers':meta,'parts':stats,'hashes':hashes,'sourceUnchanged':all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())}
(OUT/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('Source unchanged:',report['sourceUnchanged'])
