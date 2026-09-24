from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
sys.path.insert(0,str(ROOT/'art/processing_v001/tools/pylib'))
import numpy as np
import cv2
from PIL import Image,ImageDraw,ImageFont
SRC=ROOT/'art/processing_v001/front/parts'; SNAP=OUT/'source_snapshot'; SNAP.mkdir(exist_ok=True)
ORIGIN=(1620,270); SIZE=(760,960)
pos={'face_underfill':(1697,303),'Upper_eyelid_left':(2061,748),'Upper_eyelid_right':(1767,749)}
old=json.loads((SRC.parent/'manifest.json').read_text())
for section in ['layers','optionalLayers']:
 for q in old.get(section,[]):pos.setdefault(q['name'],(q['left'],q['top']))
# Optional records are not guaranteed to be under the same manifest key.
pos.update({'FILL_eye_white_R':(1757,752),'FILL_eye_white_L':(2056,752),
 'ALT_eyelash_upper_R':(1747,745),'ALT_eyelash_upper_L':(2058,745),
 'ALT_iris_R_brown':(1818,760),'ALT_iris_L_blue':(2106,760)})
names=['face_underfill','Upper_eyelid_left','Upper_eyelid_right']
for s,c in [('L','blue'),('R','brown')]:
 names += [f'FILL_eye_white_{s}',f'ALT_eyelash_upper_{s}',f'ALT_iris_{s}_{c}',f'iris_{s}_original',f'eyelash_upper_{s}_original']
ims={}; hashes={}
for n in names:
 p=SRC/(n+'.png');q=SNAP/p.name
 if not q.exists():shutil.copy2(p,q)
 assert q.read_bytes()==p.read_bytes(),f'Source changed: {n}'
 hashes[n]=hashlib.sha256(p.read_bytes()).hexdigest();ims[n]=Image.open(q).convert('RGBA')

def canvas(im,xy):
 b=Image.new('RGBA',SIZE);b.alpha_composite(im,(xy[0]-ORIGIN[0],xy[1]-ORIGIN[1]));return b

def eye(s,c,amount):
 name=f'ALT_eyelash_upper_{s}'; lash=np.asarray(ims[name]); lx,ly=pos[name]
 # Fit the inner lower edge, excluding outer lash spikes.
 xx=[]; yy=[]
 for x in range(int(lash.shape[1]*.18),int(lash.shape[1]*.82)):
  ys=np.where(lash[:,x,3]>180)[0]
  if len(ys):xx.append(x+lx);yy.append(ys[-1]+ly)
 fit=np.polyfit(np.array(xx)-lx,yy,2)
 x0=lx+(28 if s=='R' else 4);x1=lx+lash.shape[1]-(4 if s=='R' else 28)
 def curves(x):
  u=np.clip((x-x0)/(x1-x0),0,1);bow=np.sin(np.pi*u)
  op=np.polyval(fit,np.clip(x,x0,x1)-lx)
  closed=804+26*bow
  top=op*amount+closed*(1-amount)
  bottom=(804+66*bow)*amount+closed*(1-amount)
  return op,top,bottom
 # Premultiplied warp to avoid dark halos on transparent edges.
 def warp(im,xy,iscrease=False):
  src=np.array(canvas(im,xy)).astype(np.float32)/255
  gy,gx=np.indices((SIZE[1],SIZE[0]),dtype=np.float32);gx+=ORIGIN[0];gy+=ORIGIN[1]
  op,top,_=curves(gx);scale=1-.55*(1-amount)
  sy=(gy-top)/scale+op if not iscrease else gy-(top-op)*.75
  src[:,:,:3]*=src[:,:,3:4]
  out=cv2.remap(src,(gx-ORIGIN[0]).astype('float32'),(sy-ORIGIN[1]).astype('float32'),cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
  out=np.clip(out,0,1);out[:,:,:3]=np.divide(out[:,:,:3],out[:,:,3:4],out=np.zeros_like(out[:,:,:3]),where=out[:,:,3:4]>1e-6)
  return Image.fromarray(np.uint8(np.clip(out,0,1)*255+.5))
 white=canvas(ims[f'FILL_eye_white_{s}'],pos[f'FILL_eye_white_{s}'])
 ar=np.array(white);gy,gx=np.indices((SIZE[1],SIZE[0]));gx+=ORIGIN[0];gy+=ORIGIN[1]
 _,top,bottom=curves(gx)
 mask=np.clip(gy-top+.5,0,1)*np.clip(bottom-gy+.5,0,1)*(gx>=x0)*(gx<=x1)
 if amount==0:mask[:]=0
 ar[:,:,3]=np.uint8(ar[:,:,3]*mask);white=Image.fromarray(ar)
 iris=canvas(ims[f'ALT_iris_{s}_{c}'],pos[f'ALT_iris_{s}_{c}'])
 ia=np.array(iris);ia[:,:,3]=np.uint8(ia[:,:,3].astype(float)*ar[:,:,3]/255+.5);iris=Image.fromarray(ia)
 crease='Upper_eyelid_left' if s=='L' else 'Upper_eyelid_right'
 return [(f'eye_white_{s}',white,None),(f'iris_{s}',iris,None),
         (f'upper_lash_{s}',warp(ims[name],pos[name]),None),
         (f'upper_crease_{s}',warp(ims[crease],pos[crease],True),None)]

def assemble(amount):
 layers=[('face_underfill',canvas(ims['face_underfill'],pos['face_underfill']),None)]
 for s,c in [('R','brown'),('L','blue')]:layers+=eye(s,c,amount)
 result=Image.new('RGBA',SIZE);prev=None
 for name,im,clip in layers:
  show=im.copy()
  if clip:
   a=np.asarray(show).copy();a[:,:,3]=np.uint8(a[:,:,3].astype(float)*np.asarray(prev)[:,:,3]/255+.5);show=Image.fromarray(a)
  result.alpha_composite(show);prev=im
 return layers,result

states=[('open',1.0),('half',.5),('closed',0.0)];checks={};previews=[]
for label,a in states:
 folder=OUT/label;folder.mkdir(exist_ok=True);(folder/'parts').mkdir(exist_ok=True)
 layers,result=assemble(a);spec=[]
 for name,im,clip in layers:
  box=im.getbbox() or (0,0,1,1);im.crop(box).save(folder/'parts'/f'{name}.png')
  r={'name':name,'path':f'parts/{name}.png','left':box[0],'top':box[1],'visible':True}
  if clip:r['clipTo']=clip
  spec.append(r)
 # Keep full original donor parts as hidden editable references, not baked replacements.
 for n in names[1:]:
  q=ims[n];q.save(folder/'parts'/f'REF_{n}.png');xy=pos[n]
  spec.append({'name':'REF_'+n,'path':f'parts/REF_{n}.png','left':xy[0]-ORIGIN[0],'top':xy[1]-ORIGIN[1],'visible':False})
 manifest={'canvas':{'width':SIZE[0],'height':SIZE[1]},'globalOrigin':ORIGIN,'eyeOpen':a,
 'status':'Raster key-shape study; not Cubism parameter keys','layers':spec,
 'output':{'psd':f'Ren_eyes_{label}_v001.psd','flattenedPng':'assembled.png','previewPng':'preview.png','verificationJson':'psd_verification.json','previewBackground':'#657078'}}
 (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 result.save(folder/'python_composite.png');bg=Image.new('RGBA',SIZE,(101,112,120));bg.alpha_composite(result);previews.append(bg.convert('RGB'))
 checks[label]={'whitePixels':{n:int(np.count_nonzero(np.array(im)[:,:,3])) for n,im,_ in layers if n.startswith('eye_white')}}

font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
sheet=Image.new('RGB',(1500,520),(101,112,120));d=ImageDraw.Draw(sheet)
for i,((label,a),im) in enumerate(zip(states,previews)):
 tile=im.crop((100,405,680,670));tile.thumbnail((490,430));sheet.paste(tile,(i*500+5,70));d.text((i*500+15,20),f'{label.upper()} / Eye open = {a}',font=font,fill='white')
 d.text((i*500+15,350),'Character R (brown) / L (blue)',font=font,fill='white')
sheet.save(OUT/'blink_states.jpg',quality=97)
frames=[];dur=[]
for a,ms in [(1,1200),(.8,50),(.6,50),(.4,50),(.2,50),(0,140),(.2,50),(.4,50),(.6,50),(.8,50),(1,600)]:
 _,im=assemble(a);b=Image.new('RGBA',SIZE,(101,112,120));b.alpha_composite(im);b=b.crop((100,385,680,700)).convert('RGB');frames.append(b);dur.append(ms)
frames[0].save(OUT/'blink_preview.gif',save_all=True,append_images=frames[1:],duration=dur,loop=0,disposal=2)
assert all(v==0 for v in checks['closed']['whitePixels'].values())
unchanged=all(hashlib.sha256((SRC/(n+'.png')).read_bytes()).hexdigest()==h for n,h in hashes.items());assert unchanged
(OUT/'validation.json').write_text(json.dumps({'sourceHashes':hashes,'sourceUnchanged':unchanged,'states':checks,'globalOrigin':ORIGIN,'pipeline':'local raster deformation guide, 0 agents; not imported into Cubism'},indent=2),encoding='utf-8')
print(json.dumps(checks))
