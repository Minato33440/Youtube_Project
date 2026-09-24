raise SystemExit('Historical generator disabled: parts/ contains current hand-edited assets. Read parts/README.md and build a new output version; do not overwrite current parts.')
from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;BASE=ROOT/'art/processing_v001/front/parts'
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
sys.path.insert(0,str(ROOT/'art/processing_v001/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import cv2
P=OUT/'parts';P.mkdir(exist_ok=True);SNAP=OUT/'source_snapshot';SNAP.mkdir(exist_ok=True)
origin=(1620,270);size=(760,960);layers=[];hashes={}
def load(n):
 p=BASE/(n+'.png');hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();shutil.copy2(p,SNAP/p.name);return Image.open(p).convert('RGBA')
def add(n,im,xy,visible=True):
 im.save(P/(n+'.png'));layers.append({'name':n,'path':'parts/'+n+'.png','left':xy[0]-origin[0],'top':xy[1]-origin[1],'visible':visible})
def bg(im):
 b=Image.new('RGBA',im.size,(80,105,110));b.alpha_composite(im);return b.convert('RGB')
add('face_underfill',load('face_underfill'),(1697,303))
rawpath=ROOT/'art_assets/ren-stand-pony-front-4000x6000.png';raw=Image.open(rawpath).convert('RGBA');hashes[str(rawpath)]=hashlib.sha256(rawpath.read_bytes()).hexdigest()
# Original-art lower edges; sampled at the white/skin boundary, not the iris outline.
paths={'R':[(1778,834),(1794,849),(1815,861),(1840,874),(1865,875),(1890,870),(1910,854),(1928,836)],
       'L':[(2068,837),(2090,858),(2115,873),(2140,875),(2165,869),(2190,854),(2215,828)]}
eyeinfo=[]
for side,color in [('R','brown'),('L','blue')]:
 xbase=1740 if side=='R' else 2045;ybase=740;w,h=235,165
 yy,xx=np.indices((h,w),dtype=float);gx=xx+xbase;gy=yy+ybase
 pts=np.array(paths[side]);bottom=np.interp(gx,pts[:,0],pts[:,1]);bottom=cv2.GaussianBlur(bottom,(31,1),5);xmin,xmax=pts[0,0],pts[-1,0]
 # Top follows the ALT lash inner edge while the lower arc follows original art.
 lash=load('ALT_eyelash_upper_'+side);lx,ly=(1750,765) if side=='R' else (2058,762)
 la=np.array(lash);fitx=[];fity=[]
 for x in range(35,160):
  ys=np.where(la[:,x,3]>180)[0]
  if len(ys):fitx.append(x+lx);fity.append(ys[-1]+ly)
 fit=np.polyfit(np.array(fitx)-lx,fity,2);top=np.polyval(fit,gx-lx)
 alpha=np.clip(gy-top+.5,0,1)*np.clip(bottom-1-gy+.5,0,1)*(gx>=xmin)*(gx<=xmax)
 # Filled white layer is restricted to the matched aperture, avoiding polygon corners.
 wa=np.zeros((h,w,4),dtype=np.uint8);wa[:,:,:3]=(246,245,244);wa[:,:,3]=(alpha*255+.5).astype('uint8')
 white=Image.fromarray(wa);add('eye_white_'+side,white,(xbase,ybase))
 iris=load('ALT_iris_'+side+'_'+color).resize((88,92),Image.Resampling.LANCZOS)
 ix,iy=(1818,776) if side=='R' else (2105,773)
 ircanvas=Image.new('RGBA',(w,h));ircanvas.alpha_composite(iris,(ix-xbase,iy-ybase));ia=np.array(ircanvas);ia[:,:,3]=(ia[:,:,3]*alpha+.5).astype('uint8')
 add('iris_'+side,Image.fromarray(ia),(xbase,ybase));add('upper_lash_'+side,lash,(lx,ly))
 # Cut a narrow feathered strip of the original lower lid, preserving source RGB.
 band=np.clip(3.5-np.abs(gy-bottom),0,1)*np.clip((gx-xmin)/9,0,1)*np.clip((xmax-gx)/9,0,1)
 ra=np.array(raw.crop((xbase,ybase,xbase+w,ybase+h)));ra[:,:,3]=(ra[:,:,3]*band+.5).astype('uint8')
 lid=Image.fromarray(ra);bb=lid.getbbox();lid=lid.crop(bb)
 add('lower_lid_'+side,lid,(xbase+bb[0],ybase+bb[1]))
 # Wider reference strip helps manual cleanup without losing original context.
 ref=raw.crop((xbase,ybase+70,xbase+w,ybase+h));add('REF_lower_lid_source_'+side,ref,(xbase,ybase+70),False)
 add('REF_iris_full_'+side,iris,(ix,iy),False)
 eyeinfo.append({'side':side,'iris_size':[88,92],'iris_position':[ix,iy],'upper_lash_position':[lx,ly],'lower_edge_points':paths[side],'lower_lid_bbox':list(bb)})
 # Retain previous actual eyelid crease, not the newly repurposed eyebrow file.
 bd=ROOT/'art/blink_assembly_v001/open';bm=json.loads((bd/'manifest.json').read_text());q=next(q for q in bm['layers'] if q['name']=='upper_crease_'+side)
 im=Image.open(bd/q['path']).convert('RGBA');add('upper_crease_'+side,im,(1620+q['left'],270+q['top']+17))
for n,side,xy in [('Upper_eyelid_left','L',(2043,684)),('Upper_eyelid_right','R',(1752,687))]:add('brow_'+side,load(n),xy)
# Existing approved closed mouth for context.
md=ROOT/'art/mouth_motion_v002/closed';m=json.loads((md/'manifest.json').read_text());q=next(q for q in m['layers'] if q['name']=='mouth_closed');add('mouth_closed',Image.open(md/q['path']).convert('RGBA'),(1620+q['left'],270+q['top']))
canvas=Image.new('RGBA',size)
for q in layers:
 if q['visible']:canvas.alpha_composite(Image.open(OUT/q['path']).convert('RGBA'),(q['left'],q['top']))
canvas.save(OUT/'python_composite.png');bg(canvas).save(OUT/'eyes_face_preview.jpg',quality=97)
manifest={'canvas':{'width':760,'height':960},'globalOrigin':list(origin),'layers':layers,'output':{'psd':'Ren_eyes_adjust_v007.psd','flattenedPng':'assembled.png','previewPng':'preview.png','verificationJson':'psd_verification.json','previewBackground':'#50696e'}}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
# Combine without changing current hair/neck assets; user is repairing the nape separately.
pos=json.loads((ROOT/'art/pre_rig_review_20260922/placements_review.json').read_text())['positions']
for n,r in json.loads((ROOT/'art/overlap_recheck_v002/registration.json').read_text()).items():pos[n]=r['position']
pos['shirt_torso']=[1422,1231];c=Image.new('RGBA',(4000,3000))
def context_part(n):
 folder='shirt_brow_recheck_v003' if n=='shirt_torso' else 'overlap_recheck_v002' if n in ['hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C'] else 'pre_rig_review_20260922'
 path=ROOT/'art'/folder/'source_snapshot'/(n+'.png')
 return Image.open(path).convert('RGBA')
for n in ['hair_back','shirt_inside','neck-clavicle','shirt_torso','collar_R','collar_L','ear_R','ear_L']:c.alpha_composite(context_part(n),tuple(pos[n]))
c.alpha_composite(canvas,origin)
for n in ['hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C','hair_ahoge']:c.alpha_composite(context_part(n),tuple(pos[n]))
face=bg(c.crop((1460,80,2540,1700)));face.save(OUT/'face_sample.jpg',quality=97)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
compare=Image.new('RGB',(1620,720),(80,105,110));d=ImageDraw.Draw(compare)
for i,im in enumerate([bg(raw.crop((1460,80,2540,1700))),Image.open(ROOT/'art/eye_style_v006/face_with_brows.jpg'),face]):
 im=im.crop((0,160,1080,1520)).resize((540,680));compare.paste(im,(i*540,40));d.text((i*540+12,8),['Original','Before','Adjusted'][i],font=font,fill='white')
compare.save(OUT/'comparison.jpg',quality=97)
detail=Image.new('RGB',(2100,380),(80,105,110));d=ImageDraw.Draw(detail)
for i,im in enumerate([bg(raw.crop((1460,80,2540,1700))),Image.open(ROOT/'art/eye_style_v006/face_with_brows.jpg'),face]):
 detail.paste(im.crop((240,630,940,960)),(i*700,40));d.text((i*700+10,5),['Original','Before','Adjusted'][i],font=font,fill='white')
detail.save(OUT/'eyes_comparison.jpg',quality=97)
for p,sha in hashes.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha,p
(OUT/'validation.json').write_text(json.dumps({'sourceUnchanged':True,'sources':hashes,'eyes':eyeinfo},indent=2),encoding='utf8')
print('Saved',len(layers),'layers; source files unchanged')
