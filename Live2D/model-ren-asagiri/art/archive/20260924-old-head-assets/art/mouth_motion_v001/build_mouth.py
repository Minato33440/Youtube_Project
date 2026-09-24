"""Non-destructive mouth key-shape study. Never run against manually edited outputs."""
from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
sys.path.insert(0,str(ROOT/'art/processing_v001/tools/pylib'))
import numpy as np
import cv2
from PIL import Image,ImageDraw,ImageFont
SRC=ROOT/'art/processing_v001/front/parts';SPLIT=ROOT/'art/mouth_split_v002/parts'
SNAP=OUT/'source_snapshot';SNAP.mkdir(exist_ok=True)
sources={'face_underfill':SRC/'face_underfill.png','mouth_closed':SRC/'mouth_closed.png',
 'mouth_teeth_upper':SRC/'ALT_mouth_teeth_upper.png',
 **{n:SPLIT/(n+'.png') for n in ['mouth_cavity','mouth_tongue','mouth_rim_upper','mouth_rim_lower']}}
images={};hashes={}
for n,p in sources.items():
 q=SNAP/(n+'.png')
 if not q.exists():shutil.copy2(p,q)
 assert q.read_bytes()==p.read_bytes(),f'Source changed since snapshot: {p}'
 images[n]=Image.open(q).convert('RGBA');hashes[n]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':images[n].size}
ORIGIN=(1620,270);SIZE=(760,960);CENTER_X=2004;CLOSED_Y=1022
def place(im,xy):
 out=Image.new('RGBA',SIZE);out.alpha_composite(im,(xy[0]-ORIGIN[0],xy[1]-ORIGIN[1]));return out
face=place(images['face_underfill'],(1697,303))
# Keep approved open-eye study for face context; never use its old face snapshot.
eyes=Image.new('RGBA',SIZE)
eye_root=ROOT/'art/blink_assembly_v001/open'; eye_manifest=json.loads((eye_root/'manifest.json').read_text())
for q in eye_manifest['layers']:
 if q.get('visible',True) and q['name']!='face_underfill':
  p=eye_root/q['path'];im=Image.open(p).convert('RGBA');eyes.alpha_composite(im,(q['left'],q['top']))
eyes.save(SNAP/'approved_open_eyes_context.png')

# Local donor registration, including latest cropped rims.
DONOR=(250,200);parts={}
for n in ['mouth_cavity','mouth_tongue','mouth_rim_upper','mouth_rim_lower','mouth_teeth_upper']:
 im=images[n];b=Image.new('RGBA',DONOR)
 if n=='mouth_rim_lower':xy=(16,96)
 elif n=='mouth_teeth_upper':
  # Latest hand-finished teeth replace the older split teeth. Preserve proportions.
  ratio=212/im.width;im=im.resize((212,round(im.height*ratio)),Image.Resampling.LANCZOS);xy=(13,3)
 else:xy=(0,0)
 b.alpha_composite(im,xy);parts[n]=b

Y,X=np.indices((SIZE[1],SIZE[0]),dtype=np.float32);GX=X+ORIGIN[0];GY=Y+ORIGIN[1]
def remap(im,xmap,ymap):
 ar=np.asarray(im).astype('float32')/255;ar[:,:,:3]*=ar[:,:,3:4]
 out=cv2.remap(ar,xmap.astype('float32'),ymap.astype('float32'),cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
 out=np.clip(out,0,1);out[:,:,:3]=np.divide(out[:,:,:3],out[:,:,3:4],out=np.zeros_like(out[:,:,:3]),where=out[:,:,3:4]>1e-6)
 return Image.fromarray(np.uint8(np.clip(out,0,1)*255+.5))
def alpha_mul(im,mask):
 ar=np.array(im);ar[:,:,3]=np.uint8(ar[:,:,3].astype(float)*mask+.5);return Image.fromarray(ar)

closed=images['mouth_closed'];bb=closed.getbbox();closed=closed.crop(bb)
closed=place(closed,(round(CENTER_X-closed.width/2),CLOSED_Y-closed.height//2))

def mouth(amount):
 t=float(amount);width_scale=.41+.37*t;sy=max(.001,.68*t)
 sx=(GX-CENTER_X)/width_scale+121
 u=np.clip(sx/242,0,1);closed_curve=1017+5*np.sin(np.pi*u)
 top_anchor=closed_curve-t*(14+5*np.sin(np.pi*u))
 cavity=remap(parts['mouth_cavity'],sx,(GY-top_anchor)/sy)
 open_weight=min(1,t/.12);cavity=alpha_mul(cavity,open_weight)
 # Keep teeth height; clip as lips uncover them. Do not squash teeth with the gap.
 teeth=remap(parts['mouth_teeth_upper'],sx,(GY-top_anchor+38*(1-t))/.72)
 # Tongue follows the lower lip, with less vertical compression than the cavity.
 tongue_scale=.68*(.45+.55*t);bottom=top_anchor+sy*183
 tongue=remap(parts['mouth_tongue'],sx,(GY-bottom-55*(1-t))/tongue_scale+183)
 mask=np.asarray(cavity)[:,:,3]/255
 teeth_exposure=np.clip((25+85*t-np.abs(sx-121))/5,0,1)
 teeth=alpha_mul(teeth,mask*teeth_exposure);tongue=alpha_mul(tongue,mask)
 rims=[]
 for n in ['mouth_rim_upper','mouth_rim_lower']:
  ar=np.asarray(parts[n]);a=ar[:,:,3].astype(float)
  # Column centers retain line thickness while the shape closes.
  centers=np.divide((a*np.arange(DONOR[1])[:,None]).sum(0),a.sum(0),out=np.zeros(DONOR[0]),where=a.sum(0)>0)
  valid=np.where(a.sum(0)>0)[0];centers=np.interp(np.arange(DONOR[0]),valid,centers[valid])
  center=np.interp(sx,np.arange(DONOR[0]),centers)
  # Tall side strokes should shrink with the opening, not protrude at mouth corners.
  spans=np.array([np.ptp(np.where(a[:,i]>10)[0]) if np.any(a[:,i]>10) else 0 for i in range(DONOR[0])])
  keep=np.interp(sx,np.arange(DONOR[0]),np.clip((25-spans)/15,0,1))
  stroke_scale=sy+(.60+.08*t-sy)*keep
  target=top_anchor+sy*center
  im=remap(parts[n],sx,(GY-target)/np.maximum(stroke_scale,.001)+center)
  rims.append((n,alpha_mul(im,open_weight)))
 layers=[('face_underfill',face),('eyes_context',eyes),('mouth_cavity',cavity),('mouth_teeth_upper',teeth),('mouth_tongue',tongue),*rims,('mouth_closed',alpha_mul(closed,1-open_weight))]
 if t==0:
  layers=[(n,Image.new('RGBA',SIZE) if n.startswith('mouth_') and n!='mouth_closed' else im) for n,im in layers]
 comp=Image.new('RGBA',SIZE)
 for n,im in layers:comp.alpha_composite(im)
 return layers,comp

states=[('closed',0),('small',.28),('open',1)];stats={};renders=[]
for label,t in states:
 dest=OUT/label;dest.mkdir(exist_ok=True);(dest/'parts').mkdir(exist_ok=True)
 layers,comp=mouth(t);spec=[]
 for n,im in layers:
  box=im.getbbox() or (0,0,1,1);im.crop(box).save(dest/'parts'/(n+'.png'))
  spec.append({'name':n,'path':f'parts/{n}.png','left':box[0],'top':box[1],'visible':True})
 # Preserve registered full donor material for subsequent editing and Cubism masking.
 for n,im in parts.items():
  im.save(dest/'parts'/('REF_'+n+'.png'));spec.append({'name':'REF_'+n,'path':f'parts/REF_{n}.png','left':250,'top':700,'visible':False})
 manifest={'canvas':{'width':SIZE[0],'height':SIZE[1]},'globalOrigin':ORIGIN,'mouthOpen':t,
 'status':'Raster shape study, not Cubism parameter keys','layers':spec,
 'output':{'psd':f'Ren_mouth_{label}_v001.psd','flattenedPng':'assembled.png','previewPng':'preview.png','verificationJson':'psd_verification.json','previewBackground':'#657078'}}
 (dest/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');comp.save(dest/'python_composite.png')
 stats[label]={n:int(np.count_nonzero(np.asarray(im)[:,:,3])) for n,im in layers if n.startswith('mouth_')}
 renders.append(comp)

def bg(im):
 b=Image.new('RGBA',im.size,(101,112,120));b.alpha_composite(im);return b.convert('RGB')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
sheet=Image.new('RGB',(1200,430),(101,112,120));d=ImageDraw.Draw(sheet)
for i,((label,t),im) in enumerate(zip(states,renders)):
 crop=bg(im.crop((245,680,520,930))).resize((385,350));sheet.paste(crop,(i*400+7,50));d.text((i*400+12,12),f'{label.upper()} / Mouth open {t}',font=font,fill='white')
sheet.save(OUT/'mouth_states.jpg',quality=97)
face_sheet=Image.new('RGB',(1140,600),(101,112,120))
for i,im in enumerate(renders):face_sheet.paste(bg(im).resize((380,480)),(i*380,40))
face_sheet.save(OUT/'face_states.jpg',quality=96)
frames=[];dur=[]
sequence=[(0,700),(.06,70),(.12,70),(.2,70),(.28,400),(.4,90),(.6,90),(.8,90),(1,650),(.8,90),(.6,90),(.4,90),(.28,150),(.2,70),(.12,70),(.06,70),(0,700)]
for t,ms in sequence:
 _,im=mouth(t);frames.append(bg(im.crop((160,410,620,940))).resize((460,530)));dur.append(ms)
frames[0].save(OUT/'mouth_preview.gif',save_all=True,append_images=frames[1:],duration=dur,loop=0,disposal=2)
# A tiled transition view allows checking every GIF shape without playback tooling.
contacts=Image.new('RGB',(1200,720),(101,112,120));d=ImageDraw.Draw(contacts)
for i,(t,_) in enumerate(sequence[:9]):
 _,im=mouth(t);tile=bg(im.crop((255,710,515,910))).resize((260,200));x=(i%4)*300;y=(i//4)*240;contacts.paste(tile,(x+20,y+28));d.text((x+20,y+5),f'Open={t}',font=font,fill='white')
contacts.save(OUT/'transition_contact_sheet.jpg',quality=97)
for n in ['mouth_cavity','mouth_teeth_upper','mouth_tongue','mouth_rim_upper','mouth_rim_lower']:assert stats['closed'][n]==0
assert all(hashlib.sha256(p.read_bytes()).hexdigest()==hashes[n]['sha256'] for n,p in sources.items()),'Original changed'
(OUT/'validation.json').write_text(json.dumps({'sourceHashes':hashes,'sourceUnchanged':True,'states':stats,'donorLowerOffset':[16,96],'donorLatestTeeth':{'width':212,'offset':[13,3]},'globalOrigin':ORIGIN,'mouthCenterX':CENTER_X,'closedCenterY':CLOSED_Y},indent=2),encoding='utf-8')
print(json.dumps(stats))
