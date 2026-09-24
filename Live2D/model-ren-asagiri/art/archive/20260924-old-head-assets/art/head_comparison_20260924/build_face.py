from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
sys.path.insert(0,str(ROOT/'art/processing_v001/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont,ImageChops
from psd_tools import PSDImage
import cv2,numpy as np
P=ROOT/'art/eye_adjust_v007/parts';SNAP=OUT/'source_snapshot';SNAP.mkdir(exist_ok=True)
hashes={}
def load(n):
 p=P/n;hashes[n]=hashlib.sha256(p.read_bytes()).hexdigest();shutil.copy2(p,SNAP/n);return Image.open(p).convert('RGBA')
ref=load('facial_feature.png');psdp=P/'facial_feature.psd';hashes[psdp.name]=hashlib.sha256(psdp.read_bytes()).hexdigest()
psd=PSDImage.open(psdp);layers=list(psd)
def target(idx):
 l=layers[idx];c=Image.new('RGBA',ref.size);c.alpha_composite(l.composite(),(l.left,l.top));return c
def pm(im):
 a=np.array(im).astype('float32')/255;a[:,:,:3]*=a[:,:,3:4];return a
def bg(im):
 b=Image.new('RGBA',im.size,(80,105,110,255));b.alpha_composite(im);return b.convert('RGB')
mapping=[('face_underfill',0),('mouth_closed',1),('FILL_eye_white_R',2),('ALT_iris_R_brown',3),('ALT_eyelash_upper_R',4),('lower_eyelid_right',5),('upper_crease_R',6),('brow_R',7),('FILL_eye_white_L',8),('ALT_iris_L_blue',9),('ALT_eyelash_upper_L',10),('lower_eyelid_left',11),('upper_crease_L',12),('brow_L',13)]
result=Image.new('RGBA',ref.size);manifest=[]
for name,idx in mapping:
 im=load(name+'.png');tc=target(idx);l=layers[idx]
 bbox=(489,526,683,557) if name=='brow_L' else tuple(l.bbox)
 if name=='brow_L':
  mask=Image.new('L',ref.size);ImageDraw.Draw(mask).rectangle(bbox,fill=255);tc.putalpha(ImageChops.multiply(tc.getchannel('A'),mask))
 if name=='face_underfill':
  best={'pos':[l.left,l.top],'size':list(im.size),'flip':False,'score':float(np.abs(pm(im)-pm(l.composite())).mean())};chosen=im
 else:
  searchbox=(max(0,bbox[0]-30),max(0,bbox[1]-25),min(ref.width,bbox[2]+30),min(ref.height,bbox[3]+25))
  search=pm(tc.crop(searchbox));best=None
  sizes=[im.size];fit=(bbox[2]-bbox[0],bbox[3]-bbox[1])
  if fit!=im.size and .75<fit[0]/im.width<1.35 and .7<fit[1]/im.height<1.5:sizes.append(fit)
  for flip in [False,True]:
   a=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip else im
   for size in sizes:
    z=a if size==a.size else a.resize(size,Image.Resampling.LANCZOS);template=pm(z)
    # Compare the visible pixels; transparent crop margins must not influence registration.
    mask=np.repeat((template[:,:,3:4]>.1).astype('float32'),4,axis=2)
    scores=cv2.matchTemplate(search,template,cv2.TM_SQDIFF,mask=mask)/max(1,float(mask.sum()))
    v,_,loc,_=cv2.minMaxLoc(scores);v=max(0,v)
    if best is None or v<best['score']:
     best={'pos':[searchbox[0]+loc[0],searchbox[1]+loc[1]],'size':list(size),'flip':flip,'score':v};chosen=z
  print(name,best)
 result.alpha_composite(chosen,tuple(best['pos']));manifest.append({'name':name,'source':name+'.png','referenceLayer':idx,**best})
result.save(OUT/'face_sample.png');bg(result).save(OUT/'face_sample_gray.png')
bg(ref).save(OUT/'placement_reference_gray.png')
font=ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc',25)
def sheet(ims,labels,size,cols,name):
 w,h=size;c=Image.new('RGB',(w*cols,(h+50)*((len(ims)+cols-1)//cols)),(58,63,67));d=ImageDraw.Draw(c)
 for i,(im,label) in enumerate(zip(ims,labels)):
  x=i%cols*w;y=i//cols*(h+50);c.paste(im.resize(size,Image.Resampling.LANCZOS),(x,y+50));d.text((x+12,y+10),label,font=font,fill='white')
 c.save(OUT/name,quality=97)
sheet([bg(ref),bg(result)],['指定の配置見本','最新の個別PNGから再合成'],(680,907),2,'comparison.jpg')
sheet([bg(ref.crop((150,505,705,910))),bg(result.crop((150,505,705,910)))],['配置見本：目・鼻・口','最新PNG：目・鼻・口'],(832,607),2,'detail_comparison.jpg')
# The original drawing is in the same approved input directory and is used only as a comparison reference.
original=load('ren-stand-pony-front-4000x6000.png')
nosebox=(405,716,445,780);searchbox=(1900,830,2080,1050)
scores=cv2.matchTemplate(np.array(original.crop(searchbox).convert('RGB')),np.array(ref.crop(nosebox).convert('RGB')),cv2.TM_CCOEFF_NORMED)
_,nose_score,_,loc=cv2.minMaxLoc(scores)
original_origin=(searchbox[0]+loc[0]-nosebox[0],searchbox[1]+loc[1]-nosebox[1])
featurebox=(150,505,705,1015);ob=tuple(v+original_origin[i%2] for i,v in enumerate(featurebox))
sheet([bg(original.crop(ob)),bg(ref.crop(featurebox)),bg(result.crop(featurebox))],['同フォルダー内の原画','指定の配置見本','最新PNGから再合成'],(555,510),3,'original_features_comparison.jpg')
diff=np.abs(np.array(bg(ref)).astype(float)-np.array(bg(result)).astype(float))
record={'canvas':list(ref.size),'inputDirectory':str(P),'reference':'facial_feature.png','originalComparisonRegistration':{'translation':original_origin,'noseTextureScore':nose_score,'note':'Comparison alignment only; not used to assemble parts'},'layers':manifest,'sourceHashes':hashes,'sourceUnchanged':all(hashlib.sha256((P/n).read_bytes()).hexdigest()==h for n,h in hashes.items()),'meanAbsoluteRgbDifferenceToReference':float(diff.mean()),'maxAlphaDifference':int(np.abs(np.array(ref.getchannel('A')).astype(int)-np.array(result.getchannel('A')).astype(int)).max())}
(OUT/'assembly.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
assert record['sourceUnchanged']
print('MAE',record['meanAbsoluteRgbDifferenceToReference'])
