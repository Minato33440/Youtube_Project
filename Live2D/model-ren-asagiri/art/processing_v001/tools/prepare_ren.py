"""Reproducible Ren source separation. Originals are read-only.

Coordinates in body specifications use a 1000x1500 reference; head uses a
1150x1280 crop at (1400,70). Masks partition the original alpha without erosion.
Hidden-area fills and supplied alternatives are explicitly identified.
"""
from pathlib import Path
import sys, json, hashlib, time
sys.path.insert(0, str(Path(__file__).parent/'pylib'))
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'art_assets'
W,H=4000,6000
HC=(1400,70,2550,1350)
layers={}
def poly(size,points,scale=1):
    m=Image.new('L',size); ImageDraw.Draw(m).polygon([(round(x*scale),round(y*scale)) for x,y in points],fill=255)
    return np.array(m)>0
def rect(size,box):
    m=np.zeros(size[::-1],bool); x0,y0,x1,y1=map(int,box); m[y0:y1,x0:x1]=True; return m
def savepart(view,name,rgba,offset=(0,0),visible=True,note='',source=''):
    im=Image.fromarray(rgba.astype('uint8')) if isinstance(rgba,np.ndarray) else rgba.copy()
    box=im.getchannel('A').getbbox()
    if box is None: raise ValueError('Empty '+name)
    im=im.crop(box); p=OUT/view/'parts'/f'{name}.png'; p.parent.mkdir(parents=True,exist_ok=True); im.save(p)
    item=dict(name=name,path=str(p.relative_to(OUT/view)).replace('\\','/'),left=offset[0]+box[0],top=offset[1]+box[1],visible=visible,note=note,source=source)
    layers.setdefault(view,[]).append(item)
    return item
def masked(arr,mask):
    a=arr.copy();a[:,:,3]=np.where(mask,a[:,:,3],0);a[a[:,:,3]==0,:3]=0;return a
def headmask_to_full(m):
    f=np.zeros((H,W),bool); f[70:1350,1400:2550]=m; return f
def paste(im,other,xy):
    im.alpha_composite(other,xy);return im
def fillholes(arr,mask):
    a=arr.copy(); a[:,:,:3]=cv2.inpaint(np.ascontiguousarray(a[:,:,:3]),mask.astype('uint8')*255,9,cv2.INPAINT_TELEA);return a
def make_view(view,src):
    original=np.array(Image.open(ASSETS/src).convert('RGBA'))
    remaining=original[:,:,3]>0
    # These masks partition existing visible pixels; boundary/line pixels are retained.
    body=[]
    def take(name,points):
        nonlocal remaining
        m=poly((W,H),points,4)&remaining; remaining &=~m
        body.append((name,masked(original,m)))
    # L/R are CHARACTER sides (back view therefore reverses screen mapping).
    sl='R' if view=='front' else 'L'; sr='L' if view=='front' else 'R'
    take('shoe_'+sl,[(300,1320),(405,1308),(463,1321),(482,1500),(300,1500)])
    take('shoe_'+sr,[(517,1321),(569,1308),(694,1330),(700,1500),(510,1500)])
    take('hand_'+sl,[(130,735),(229,680),(272,701),(279,813),(140,841)])
    take('hand_'+sr,[(726,699),(768,680),(866,735),(858,840),(722,814)])
    take('forearm_'+sl,[(130,750),(238,540),(308,536),(337,586),(279,716)])
    take('forearm_'+sr,[(665,585),(693,536),(764,540),(865,750),(722,716)])
    take('upper_arm_'+sl,[(245,630),(291,458),(375,480),(376,558),(317,596)])
    take('upper_arm_'+sr,[(624,480),(711,458),(760,630),(683,596),(624,558)])
    take('belt',[(392,610),(451,620),(547,620),(607,610),(609,648),(390,648)])
    take('trousers_'+sl,[(350,640),(498,640),(501,779),(474,1400),(345,1400)])
    take('trousers_'+sr,[(498,640),(650,640),(656,1400),(500,1400),(501,779)])
    take('sleeve_'+sl,[(360,337),(368,389),(395,473),(381,511),(300,484),(298,408)])
    take('sleeve_'+sr,[(638,337),(704,408),(706,484),(620,511),(606,473),(631,389)])
    if view=='front':
        take('collar_'+sl,[(470,282),(471,319),(488,358),(501,381),(477,370),(463,350),(429,362),(444,322)])
        take('collar_'+sr,[(528,282),(554,322),(574,362),(536,350),(520,372),(501,389),(497,378),(527,320)])
        take('neck',[(470,268),(533,268),(536,335),(520,363),(499,389),(470,348),(458,310)])
    else:
        take('collar_back',[(459,278),(537,278),(560,314),(442,314)])
    take('shirt_torso',[(359,314),(640,314),(650,653),(350,653)])
    # Retain uncovered head pixels in head workflow; no whole-character layer in PSD.
    head=original[70:1350,1400:2550].copy()
    head[:,:,3]=np.where(remaining[70:1350,1400:2550],head[:,:,3],0)
    remaining[70:1350,1400:2550]=False
    if remaining.any():
        # Source scraps are retained in a separate hidden review layer, not silently deleted.
        savepart(view,'REVIEW_source_residual',masked(original,remaining),visible=False,note='Unassigned exterior pixels; retained for review',source=src)
    for n,a in body:savepart(view,n,a,source=src)
    return original,head

def scalp(view):
    n='ren-stand-pony-nohair-4000x6000.png' if view=='front' else 'ren-stand-pony-back-nohair-4000x6000.png'
    a=np.array(Image.open(ASSETS/n).convert('RGBA').crop(HC))
    # Exterior flood fill from corners; no global erosion of artwork.
    rgb=a[:,:,:3]; bg=rgb[0,0].astype(int); delta=np.max(np.abs(rgb.astype(int)-bg),axis=2)
    eligible=(delta<22).astype('uint8')
    flooded=eligible.copy();cv2.floodFill(flooded,None,(0,0),2)
    a[:,:,3]=np.where(flooded==2,0,255)
    # Remove only below head/neck region.
    a[1080:,:,3]=0
    if view=='front':
        # nohair eyes are 45px above source; align on eye centers. Mouth/chin differ slightly.
        m=np.zeros(a.shape[:2],np.uint8)
        cv2.rectangle(m,(340,553),(863,754),255,-1)
        cv2.rectangle(m,(539,869),(673,934),255,-1)
        a=fillholes(a,m>0)
        shifted=np.zeros_like(a);shifted[45:]=a[:-45];a=shifted
    return a,n

def front_head(original,head):
    view='front'; h,w=head.shape[:2]; yy,xx=np.mgrid[:h,:w]
    # Segment blue hair while protecting the iris rectangles; inspect mask output.
    r,g,b=[head[:,:,i].astype(int) for i in range(3)]
    potential_skin=poly((w,h),[(417,410),(800,410),(840,676),(891,738),(949,750),(949,835),(897,921),(804,980),(703,1050),(606,1098),(495,1050),(408,980),(346,922),(275,871),(254,800),(259,744),(331,680)])
    hair=(((b>r+3)&(b>g)&(r<185))|~potential_skin)&(yy<1100)&(head[:,:,3]>0)
    # Protect the blue iris only, not a rectangle that would leave side hair on skin.
    blue_iris=((xx-748)/48)**2+((yy-745)/60)**2<1
    hair[blue_iris]=False
    hair=cv2.morphologyEx(hair.astype('uint8'),cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))>0
    hair=(cv2.dilate(hair.astype('uint8'),np.ones((3,3),np.uint8))>0)&(head[:,:,3]>0)
    ah=poly((w,h),[(180,0),(650,0),(647,138),(610,135),(588,153),(551,139),(454,152),(315,206),(209,313)])&hair
    rest=hair&~ah
    # Boundary follows the three major front locks. Side/rear fragments get separate layers.
    center=poly((w,h),[(548,218),(606,215),(674,278),(709,399),(727,592),(706,711),(665,768),(695,791),(615,778),(552,728),(526,645),(503,521),(494,422),(495,328)])&rest
    rest &=~center
    sideR=(xx<450)&(yy>450)&rest
    sideL=(xx>760)&(yy>450)&rest
    rear=(yy>892)&rest;sideR &=~rear;sideL &=~rear
    rest &=~(sideR|sideL|rear)
    leftfront=rest&(xx<600);rightfront=rest&~leftfront
    hair_specs=[('hair_back',rear),('hair_side_R',sideR),('hair_side_L',sideL),('hair_front_R',leftfront),('hair_front_L',rightfront),('hair_front_C',center),('hair_ahoge',ah)]
    skinmask=(head[:,:,3]>0)&~hair
    # Separate ears from the visible skin. Complete-ear donors underneath.
    earR=poly((w,h),[(254,743),(318,752),(398,921),(353,930),(285,875),(264,831)])&skinmask
    earL=poly((w,h),[(918,735),(957,785),(933,852),(849,922),(811,908),(846,841)])&skinmask
    skinmask &=~(earR|earL)
    base,n=scalp(view)
    # Clip donor fill to original silhouette; no inadvertent change of ear/face outline.
    # Donor underfills must not turn the source antialias edge opaque.
    allhead=head[:,:,3]==255
    base[:,:,3]=np.where(allhead,base[:,:,3],0)
    er=poly((w,h),[(254,640),(326,650),(404,905),(352,930),(257,839)])
    el=poly((w,h),[(872,641),(945,640),(953,840),(849,930),(806,905)])
    savepart(view,'ear_R',masked(base,er),HC[:2],note='No-hair donor aligned +45px Y; edge finishing required',source=n)
    savepart(view,'ear_L',masked(base,el),HC[:2],note='No-hair donor aligned +45px Y; edge finishing required',source=n)
    base[:,:,3]=np.where(er|el,0,base[:,:,3])
    savepart(view,'face_underfill',base,HC[:2],note='Inpainted donor forehead/skin under source surface; inspect during deformation',source=n)
    face=masked(head,skinmask)
    features=[]
    def feature(name,mask):
        nonlocal face
        mask &=face[:,:,3]>0
        features.append((name,masked(head,mask)))
        return mask
    masks=[]
    masks.append(feature('brow_R',poly((w,h),[(343,624),(408,612),(494,620),(501,650),(397,647),(343,662)])))
    masks.append(feature('brow_L',poly((w,h),[(661,612),(752,611),(842,633),(841,660),(741,642),(662,646)])))
    eyeR=poly((w,h),[(333,692),(369,682),(411,682),(467,687),(508,709),(537,750),(508,799),(404,809),(351,774)])
    eyeL=poly((w,h),[(656,747),(679,710),(715,690),(782,682),(832,693),(865,716),(847,761),(795,803),(700,802)])
    mouth=poly((w,h),[(541,926),(653,925),(666,967),(542,973)])
    for side,em in [('R',eyeR),('L',eyeL)]:
        # Original appearance decomposed into sclera, iris, upper contour.
        valid=em&skinmask
        iriscenter=(462,747) if side=='R' else (748,745)
        iris=(((xx-iriscenter[0])/44)**2+((yy-iriscenter[1])/56)**2<1)&valid
        upperpoly=poly((w,h),[(328,675),(433,666),(500,687),(537,733),(529,755),(503,727),(471,713),(409,711),(372,733),(345,758)]) if side=='R' else poly((w,h),[(650,737),(688,696),(743,669),(836,681),(870,708),(849,751),(820,720),(787,708),(721,712),(682,733)])
        upper=upperpoly&valid; iris &=~upper
        sclera=valid&~(iris|upper)
        features.extend([(f'eye_white_{side}',masked(head,sclera)),(f'iris_{side}_original',masked(head,iris)),(f'eyelash_upper_{side}_original',masked(head,upper))])
        masks.append(valid)
    masks.append(feature('mouth_closed',mouth))
    union=np.logical_or.reduce(masks)
    # Fill feature cavities on skin surface; retain original features in their own layers.
    face=fillholes(face,union)
    savepart(view,'face_surface',face,HC[:2],note='Original skin, with eye/brow/mouth cavities inpainted; repaint review required',source='front original')
    savepart(view,'ear_R_surface',masked(head,earR),HC[:2],source='front original')
    savepart(view,'ear_L_surface',masked(head,earL),HC[:2],source='front original')
    # Complete white fills sit BELOW iris/lash layers when enabled for gaze work.
    for side,em in [('R',eyeR),('L',eyeL)]:
        fill=np.zeros_like(head);fill[:,:,:3]=(246,245,244);fill[:,:,3]=np.where(em&skinmask,255,0)
        savepart(view,'FILL_eye_white_'+side,fill,HC[:2],False,'Complete sclera fill for gaze rig; below all eye features, retouch shadow')
    for n,a in features:savepart(view,n,a,HC[:2],source='front original')
    for side,fn,x in [('R','right-eye.png',1731),('L','left-eye.png',2058)]:
        im=Image.open(ASSETS/'eye_parts'/fn).convert('RGBA').resize((197,131),Image.Resampling.LANCZOS)
        savepart(view,'ALT_whole_eye_'+side,im,(x,748),False,'Aligned whole-eye reference; switch off original eye and other alternatives before enabling',fn)
    # Alternative supplied parts: positioned at the original eyes, initially hidden.
    for side,color,fn,x in [('R','brown','brown-right-eyeball.png',1818),('L','blue','blue-left-eyeball.png',2106)]:
        im=Image.open(ASSETS/'eye_parts'/fn).convert('RGBA').resize((88,112),Image.Resampling.LANCZOS)
        savepart(view,f'ALT_iris_{side}_{color}',im,(x,760),False,'Full iris candidate, requires eye-white clipping when activated',fn)
        fn=f'Upper_{"right" if side=="R" else "left"}_eyelash.png'
        im=Image.open(ASSETS/'eye_parts'/fn).convert('RGBA').resize((197,80),Image.Resampling.LANCZOS)
        savepart(view,f'ALT_eyelash_upper_{side}',im,(1731 if side=='R' else 2058,745),False,'User composite candidate, aligned approximately; retain for editor adjustment',fn)
    # Mouth donor is local to the mouth and scaled around source mouth center.
    laugh=np.array(Image.open(ASSETS/'ren-stand-pony-laugh-4000x6000.png').convert('RGBA').crop(HC))
    mouthshape=poly((w,h),[(492,863),(539,851),(625,851),(701,861),(724,880),(715,950),(684,1007),(640,1038),(580,1042),(532,1018),(499,971),(484,911)])
    teeth=poly((w,h),[(501,864),(543,857),(625,857),(700,868),(706,884),(693,902),(677,895),(653,888),(540,889),(524,902),(506,894)])&mouthshape
    tongue=poly((w,h),[(529,966),(559,944),(606,938),(645,946),(678,967),(673,996),(642,1019),(594,1025),(555,1016),(534,996)])&mouthshape
    rim=mouthshape&~(cv2.erode(mouthshape.astype('uint8'),np.ones((11,11),np.uint8))>0)
    cavity=mouthshape&~(teeth|tongue|rim)
    ma=masked(laugh,mouthshape)
    # Remove donors from cavity and inpaint within the interior so they can move independently.
    cavitybase=fillholes(ma,teeth|tongue);cavitybase[:,:,3]=np.where(mouthshape&~rim,255,0)
    for name,a in [('mouth_interior',cavitybase),('mouth_tongue',masked(laugh,tongue)),('mouth_teeth_upper',masked(laugh,teeth)),('mouth_open_outline',masked(laugh,rim))]:
        # 75% scaling for a moderate opening; retain complete original donor separately.
        patch=Image.fromarray(a).crop((478,846,732,1050)).resize((190,153),Image.Resampling.LANCZOS)
        savepart(view,'ALT_'+name,patch,(1908,958),False,'Mouth donor scaled 0.75; aligned to source mouth center, closed mouth must be hidden on use','laugh')
    for n,m in hair_specs:savepart(view,n,masked(head,m),HC[:2],note='Source hair partition; roots/overlaps need deformation-specific finishing',source='front original')
    Image.fromarray(hair.astype('uint8')*255).save(OUT/'inspection'/'front_hair_mask.png')

def back_head(original,head):
    view='back';h,w=head.shape[:2];yy,xx=np.mgrid[:h,:w]
    under,n=scalp(view)
    under[:,:,3]=np.where(head[:,:,3]==255,under[:,:,3],0)
    earL=poly((w,h),[(250,622),(336,638),(405,861),(355,902),(251,820)])
    earR=poly((w,h),[(856,623),(949,630),(953,823),(845,901),(790,865)])
    savepart(view,'ear_L',masked(under,earL),HC[:2],note='No-hair back donor; outline restricted to source silhouette',source=n)
    savepart(view,'ear_R',masked(under,earR),HC[:2],note='No-hair back donor; outline restricted to source silhouette',source=n)
    under[:,:,3]=np.where(earL|earR,0,under[:,:,3])
    savepart(view,'head_neck_underfill',under,HC[:2],note='No-hair rear scalp/neck underfill',source=n)
    a=head[:,:,3]>0
    ah=poly((w,h),[(560,0),(995,0),(995,296),(935,277),(892,161),(742,113),(630,128),(605,180),(573,178)])&a
    a &=~ah
    sideL=poly((w,h),[(0,300),(374,315),(409,751),(465,1050),(100,1140)])&a
    sideR=poly((w,h),[(796,299),(1150,300),(1149,1140),(752,1052),(803,748)])&a
    center=a&~(sideL|sideR)
    for n,m in [('hair_back_L',sideL),('hair_back_R',sideR),('hair_back_C',center),('hair_ahoge',ah)]:savepart(view,n,masked(head,m),HC[:2],source='back original')

def render(view):
    im=Image.new('RGBA',(W,H))
    for l in layers[view]:
        if l['visible']:im.alpha_composite(Image.open(OUT/view/l['path']), (l['left'],l['top']))
    im.save(OUT/view/'assembled.png')
    im.crop(HC).save(OUT/'inspection'/f'{view}_assembled_head.png')
    if view=='front':
        for mode in ['open_mouth','eye_candidates','under_hair']:
            alt=Image.new('RGBA',(W,H))
            for l in layers[view]:
                visible=l['visible'];name=l['name']
                if mode=='open_mouth':
                    if name=='mouth_closed':visible=False
                    if name.startswith('ALT_mouth_'):visible=True
                elif mode=='eye_candidates':
                    if name.startswith(('eye_white_','iris_','eyelash_')):visible=False
                    if name.startswith('ALT_whole_eye_'):visible=True
                elif mode=='under_hair':
                    if name.startswith('hair_'):visible=False
                if visible:alt.alpha_composite(Image.open(OUT/view/l['path']),(l['left'],l['top']))
            alt.crop(HC).save(OUT/'inspection'/f'{view}_{mode}.png')
    canvas=Image.new('RGBA',(1000,1500),(110,110,110,255));canvas.alpha_composite(im.resize(canvas.size));canvas.convert('RGB').save(OUT/view/'preview.jpg',quality=94)
    m={'canvas':{'width':W,'height':H},'coordinateConvention':'character sides; canvas top-left pixel origin','layers':layers[view],'output':{'psd':f'Ren_{view}_parts_v001.psd','flattenedPng':f'Ren_{view}_parts_v001.png','previewPng':f'Ren_{view}_preview.png','verificationJson':'psd_verification.json'}}
    (OUT/view/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    start=time.time()
    hashes={str(p.relative_to(ASSETS)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ASSETS.rglob('*.png')}
    for v in ['front','back']:
        original,head=make_view(v,f'ren-stand-pony-{v}-4000x6000.png')
        (front_head if v=='front' else back_head)(original,head)
        render(v)
    (OUT/'source_hashes.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'seconds':round(time.time()-start,1),'layers':{k:len(v) for k,v in layers.items()}},indent=2))
if __name__=='__main__':main()
