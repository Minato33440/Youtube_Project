"""Non-destructive mouth separation and neck/collar review of Boss's repaired PNGs."""
from pathlib import Path
import sys, json, hashlib, shutil
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
BASE=ROOT/'art/processing_v001/front'
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
sys.path.insert(0,str(ROOT/'art/processing_v001/tools/pylib'))
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
from psd_tools import PSDImage

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
names=['ALT_mouth_interior.png','neck-clavicle.png','collar_L.png','collar_R.png','shirt_inside.png']
snap=OUT/'source_snapshot';snap.mkdir(exist_ok=True)
for n in names:
    if not (snap/n).exists():shutil.copy2(BASE/'parts'/n,snap/n)
source_hashes={n:sha(snap/n) for n in names}
im=Image.open(snap/names[0]).convert('RGBA');a=np.array(im);h,w=a.shape[:2]

def smooth_mask(points):
    # Closed Catmull-Rom curves, supersampled for subpixel mask edges.
    p=np.array(points,float); path=[]
    for i in range(len(p)):
        p0,p1,p2,p3=p[(i-1)%len(p)],p[i],p[(i+1)%len(p)],p[(i+2)%len(p)]
        for t in np.linspace(0,1,24,endpoint=False):
            path.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
    mask=Image.new('L',(w*8,h*8));ImageDraw.Draw(mask).polygon([(round(x*8),round(y*8)) for x,y in path],fill=255)
    return np.asarray(mask.resize((w,h),Image.Resampling.LANCZOS)).astype(float)/255

# Boundaries read from the actual 239x187 painted donor, not from the old mouth.
outer=smooth_mask([(3,29),(10,22),(23,16),(56,10),(119,4),(179,9),(214,16),(237,27),(237,55),(229,90),(214,122),(191,154),(163,176),(123,186),(85,180),(58,166),(34,144),(18,115),(7,80),(2,49)])
inner=smooth_mask([(7,31),(17,21),(55,13),(120,7),(180,12),(220,22),(234,31),(233,61),(224,91),(211,119),(190,150),(162,172),(122,180),(85,174),(58,160),(36,140),(22,113),(11,80),(6,51)])
teeth=smooth_mask([(19,15),(56,8),(119,3),(182,8),(219,16),(220,32),(212,44),(204,49),(194,48),(184,38),(165,33),(126,31),(87,32),(66,35),(51,40),(46,49),(33,48),(23,42),(19,31)])
tongue=smooth_mask([(42,111),(57,98),(78,89),(96,85),(122,87),(144,84),(168,89),(187,101),(197,116),(197,131),(185,146),(166,158),(143,169),(119,173),(92,169),(68,159),(51,146),(41,132)])
# The lower rim contains the white lip-edge highlight, not a lower-teeth asset.
lower_area=np.zeros((h,w),np.float32)
boundary=[(0,110),(26,113),(37,111),(39,127),(45,143),(63,158),(90,171),(119,176),(146,171),(170,161),(190,146),(200,130),(201,114),(215,114),(239,108),(239,187),(0,187)]
tmp=Image.new('L',(w*8,h*8));ImageDraw.Draw(tmp).polygon([(int(x*8),int(y*8)) for x,y in boundary],fill=255)
lower_area=np.array(tmp.resize((w,h),Image.Resampling.LANCZOS))/255.
lower_mask=np.maximum(1-inner,lower_area)*outer
lower_mask[:108]=0
upper_mask=(1-inner)*outer
upper_mask[108:]=0

parts=OUT/'parts';parts.mkdir(exist_ok=True)
clean_alpha=np.minimum(a[:,:,3].astype(float),outer*255)
cavity_rgb=np.array(a[62,120,:3],float)
# A complete dark backing fills all space previously hidden by teeth and tongue.
fill=np.zeros_like(a);fill[:,:,:3]=cavity_rgb;fill[:,:,3]=np.round(clean_alpha*inner).astype('uint8')
# Keep this backing entirely clean: source boundary fragments must not survive
# when the teeth or tongue move away. Source cavity was a flat painted color.
rgb=a[:,:,:3].astype(float)
pink=np.clip((rgb[:,:,0]-rgb[:,:,1]-12)/12,0,1)
tongue*=pink
# The white arc at the top belongs to the teeth, not to the upper mouth rim.
upper_mask*=np.clip((170-rgb.mean(axis=2))/30,0,1)
result={'mouth_cavity':Image.fromarray(fill)}
for name,mask in [('mouth_teeth_upper',teeth),('mouth_tongue',tongue),('mouth_rim_upper',upper_mask),('mouth_rim_lower',lower_mask)]:
    b=a.copy();b[:,:,3]=np.round(clean_alpha*np.clip(mask,0,1)).astype('uint8');b[b[:,:,3]==0,:3]=0
    result[name]=Image.fromarray(b)
for n,img in result.items():img.save(parts/f'{n}.png')
composite=Image.new('RGBA',im.size)
for img in result.values():composite.alpha_composite(img)
composite.save(OUT/'mouth_assembled.png')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
def panel(img,size=(520,370)):
    pic=img.copy();pic.thumbnail(size,Image.Resampling.LANCZOS)
    if pic.size==img.size:
        f=min(size[0]/pic.width,size[1]/pic.height);pic=pic.resize((round(pic.width*f),round(pic.height*f)),Image.Resampling.NEAREST)
    bg=Image.new('RGBA',size,(85,105,110,255));bg.alpha_composite(pic,((size[0]-pic.width)//2,(size[1]-pic.height)//2));return bg.convert('RGB')
tiles=[('SOURCE painted mouth',im),('SPLIT layers assembled',composite)]+list(result.items())
sheet=Image.new('RGB',(1120,440*4),(65,75,80));d=ImageDraw.Draw(sheet)
for i,(name,img) in enumerate(tiles):
    x=(i%2)*560;y=(i//2)*440;sheet.paste(panel(img),(x+20,y+50));d.text((x+20,y+15),name,font=font,fill='white')
sheet.save(OUT/'mouth_parts_review.jpg',quality=96)
manifest={'canvas':{'width':w,'height':h},'coordinateConvention':'donor-local; identical 239x187 PNG canvases, origin 0,0; global face registration pending',
 'layers':[{'name':n,'path':f'parts/{n}.png','left':0,'top':0,'visible':True} for n in result],
 'output':{'psd':'Ren_mouth_split_v002.psd','flattenedPng':'mouth_psd_assembled.png','previewPng':'mouth_psd_preview.png','verificationJson':'psd_verification.json'}}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

# Review only: align the retained neck/collar source texture against old PSD.
old={l.name:l for l in PSDImage.open(BASE/'Ren_front_parts_v001.psd')}
placements={}
for new_name,old_name in [('neck-clavicle','neck'),('collar_L','collar_L'),('collar_R','collar_R')]:
    new=Image.open(snap/f'{new_name}.png').convert('RGBA');ref=old[old_name].topil().convert('RGBA')
    # Match a small retained feature patch. Avoid repainted / deleted regions.
    roi={'neck-clavicle':(90,230,180,320),'collar_L':(180,170,280,260),'collar_R':(35,180,110,250)}[new_name]
    sample=ref.crop(roi);target=Image.new('RGBA',(new.width+200,new.height+200));target.alpha_composite(new,(100,100))
    aa=np.array(sample);bb=np.array(target);mask=(aa[:,:,3]>245).astype('uint8')*255
    score=cv2.matchTemplate(bb[:,:,:3],aa[:,:,:3],cv2.TM_SQDIFF_NORMED,mask=mask);score=np.nan_to_num(score,nan=1,posinf=1,neginf=1)
    error,_,loc,_=cv2.minMaxLoc(score)
    placements[new_name]={'left':old[old_name].left+roi[0]-loc[0]+100,'top':old[old_name].top+roi[1]-loc[1]+100,'matchingError':error,'status':'provisional review only'}
placements['shirt_inside']={'left':1716,'top':1128,'status':'manual review placement only; no global coordinates supplied'}
review=Image.new('RGBA',(4000,2000))
for n in ['shirt_inside','neck-clavicle','collar_R','collar_L']:
    p=placements[n];review.alpha_composite(Image.open(snap/f'{n}.png').convert('RGBA'),(p['left'],p['top']))
review.crop((1660,1000,2350,1680)).save(OUT/'neck_collar_overlay.png')
with_shirt=Image.new('RGBA',(4000,2000))
for n in ['shirt_torso']:
    l=old[n];with_shirt.alpha_composite(l.topil().convert('RGBA'),(l.left,l.top))
with_shirt.alpha_composite(review)
with_shirt.crop((1550,1000,2450,1750)).save(OUT/'neck_collar_with_shirt.png')
reviewtiles=[(n,Image.open(snap/f'{n}.png').convert('RGBA')) for n in ['neck-clavicle','collar_R','collar_L','shirt_inside']]
reviewtiles.append(('OVERLAY / provisional positions',review.crop((1660,1000,2350,1680))))
reviewtiles.append(('WITH torso / provisional positions',with_shirt.crop((1550,1000,2450,1750))))
sheet=Image.new('RGB',(1120,480*3),(65,75,80));d=ImageDraw.Draw(sheet)
for i,(n,img) in enumerate(reviewtiles):
    x=(i%2)*560;y=(i//2)*480;sheet.paste(panel(img,(520,410)),(x+20,y+50));d.text((x+20,y+15),n,font=font,fill='white')
sheet.save(OUT/'neck_collar_review.jpg',quality=96)
(OUT/'neck_review_placements.json').write_text(json.dumps(placements,indent=2),encoding='utf-8')
unchanged=all(sha(BASE/'parts'/n)==source_hashes[n] for n in names)
report={'sourceHashes':source_hashes,'sourceFilesUnchanged':unchanged,'canvas':[w,h],'layers':list(result),'neckPlacementEstimates':placements,
 'alphaBounds':{n:img.getbbox() for n,img in result.items()},'hiddenCavityFillRGB':cavity_rgb.tolist(),
 'limitations':['Cutout-resolution 239x187 retained; no artificial upscale','Global placement and Cubism rigging not changed','New cavity underpainting is flat source-sampled color','Lower white rim retained for Boss finishing']}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert unchanged,'Source changed during review; inspect before continuing'
print(json.dumps(report,indent=2))
