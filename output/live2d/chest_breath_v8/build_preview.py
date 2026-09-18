"""Render the native Cubism chest-breath rig and model-only previews."""
from pathlib import Path
import argparse,csv,hashlib,json,math,os,shutil,subprocess,time
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
PREVIOUS=OUT.parent/'narration_adjustment_v1'
OLD_RIG=OUT.parent/'chest_breath_v3/Risa_chest_breath.model3.json'
MODEL=OUT/'Risa_chest_breath.model3.json'
EXPORTS=ROOT/'Politics_Economics/2026-09-09_fiscal_policy/exports'
FPS=30
SIZE=(1152,1536)
CROP=(192,0,960,1080)
BG=(24,32,44,255)
CHANNELS={'ParamMouthOpenY':'mouth_open_y','ParamMouthForm':'mouth_form',
          'ParamEyeLOpen':'eye_l_open','ParamEyeROpen':'eye_r_open',
          'ParamBreath':'breath','ParamAngleZ':'angle_z'}

def write(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def ffmpeg(args): subprocess.run(['ffmpeg','-y','-nostdin','-v','error',*map(str,args)],check=True)

class Renderer:
    def __init__(self):
        import pygame
        import live2d.v3 as live2d
        self.pg=pygame; self.l2d=live2d
        pygame.display.init();live2d.init();pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE,8)
        pygame.display.set_mode(SIZE,pygame.OPENGL|pygame.DOUBLEBUF|pygame.HIDDEN);live2d.glInit()
        self.model=None
    def load(self,path):
        if self.model is not None:
            self.model.DestroyRenderer();self.model=None
        self.model=self.l2d.LAppModel();self.model.LoadModelJson(str(path));self.model.Resize(*SIZE)
        self.model.SetAutoBlinkEnable(False);self.model.SetAutoBreathEnable(False)
    def frame(self,values,dt=1/FPS,motion=False):
        from OpenGL.GL import glReadPixels,GL_RGBA,GL_UNSIGNED_BYTE,glFinish
        self.pg.event.pump()
        if not motion:
            for param,key in CHANNELS.items():self.model.SetParameterValue(param,float(values[key]))
        self.model._model.Update(dt)
        self.l2d.clearBuffer(0,0,0,0);self.model.Draw();glFinish()
        pixels=glReadPixels(0,0,*SIZE,GL_RGBA,GL_UNSIGNED_BYTE)
        rgba=np.frombuffer(pixels,np.uint8).reshape(SIZE[1],SIZE[0],4).copy()
        alpha=rgba[:,:,3:4].astype(np.float32)
        rgba[:,:,:3]=np.clip(np.rint(rgba[:,:,:3].astype(np.float32)*255/np.maximum(alpha,1)),0,255).astype(np.uint8)
        return Image.fromarray(rgba).transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop(CROP)
    def close(self):
        if self.model is not None:self.model.DestroyRenderer();self.model=None
        self.l2d.dispose();self.pg.quit()

def composite(im):
    canvas=Image.new('RGBA',(1080,1080),BG);canvas.alpha_composite(im,(156,0));return canvas.convert('RGB')

def calibration():
    cases=[]
    for breath in [0,.3,.6,1]:
        cases.append(dict(mouth_open_y=0,mouth_form=0,eye_l_open=1,eye_r_open=1,breath=breath,angle_z=0))
    for angle in [-8.4,8.4]:
        cases.append(dict(mouth_open_y=.958,mouth_form=-.55,eye_l_open=1,eye_r_open=1,breath=1,angle_z=angle))
    folder=OUT/'calibration';folder.mkdir(exist_ok=True)
    renderer=Renderer();collections={}
    try:
        for label,path in [('before',OLD_RIG),('after',MODEL)]:
            renderer.load(path);ims=[]
            for i,c in enumerate(cases):
                im=renderer.frame(c);im.save(folder/f'{label}_{i}.png');ims.append(im)
            collections[label]=ims
    finally:renderer.close()
    metrics=[]
    sheet=Image.new('RGB',(360*4,510*3),(222,222,222));draw=ImageDraw.Draw(sheet)
    for i,c in enumerate(cases):
        a=np.array(collections['before'][i]);b=np.array(collections['after'][i])
        delta=np.max(np.abs(a.astype(int)-b.astype(int)),axis=2)
        ys,xs=np.nonzero(delta>3)
        mask=np.array(Image.fromarray(a[:,:,3]).filter(ImageFilter.MinFilter(21)))>250
        holes=int(np.sum(mask&(b[:,:,3]<240)))
        metrics.append({'case':c,'changed_bbox_xyxy':None if len(xs)==0 else [int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())],
                        'head_max_pixel_difference':int(delta[:300].max()),
                        'new_interior_transparency_pixels':holes,'mean_chest_pixel_difference':float(delta[430:760,200:570].mean())})
        for j,label in enumerate(['before','after']):
            x=(i%2*2+j)*360;y=i//2*510
            pic=composite(collections[label][i]).resize((360,360))
            sheet.paste(pic,(x,y+25))
            chest=collections[label][i].crop((150,330,620,800)).resize((140,140))
            tile=Image.new('RGBA',chest.size,BG);tile.alpha_composite(chest)
            sheet.paste(tile.convert('RGB'),(x+110,y+370))
            draw.text((x+5,y+5),f'{label} Breath={c["breath"]} AngleZ={c["angle_z"]}',fill='black')
    sheet.save(OUT/'calibration_review.jpg',quality=95)
    # Global breath scaling was removed, so compare the new rig to itself.
    neutral=np.array(collections['after'][0]).astype(int)
    fixed=[]
    for i in range(4):
        b=np.array(collections['after'][i]).astype(int)
        d=np.abs(neutral-b)
        fixed.append({'breath':cases[i]['breath'],
                      'head_max_difference':int(d[:330].max()),
                      'top_collar_mean_difference':float(d[350:380,350:420].mean()),
                      'top_collar_max_difference':int(d[350:380,350:420].max())})
    assert all(m['head_max_difference']<=1 for m in fixed),fixed
    assert all(m['top_collar_mean_difference']<1 for m in fixed),fixed
    delta=np.abs(np.array(collections['before'][3]).astype(int)-np.array(collections['after'][3]).astype(int))
    assert delta[400:510,320:450,:3].mean()>.3
    assert delta[730:815,280:500,:3].mean()>.3
    assert delta[850:1000,200:570].max()==0
    write(OUT/'calibration_verification.json',{'passed':True,'cases':metrics,'fixed_neck_checks':fixed,'scope':'v3/v8 same-input comparison isolates added knit folds. Fixed checks cover the face and top collar only; internal collar folds intentionally move. Belt comparison y850:1000 must match v3.'})
    print(json.dumps(metrics,ensure_ascii=False,indent=2),flush=True)

def motion(rows,path):
    curves=[]
    for param,key in CHANNELS.items():
        seg=[0.,float(rows[0][key])]
        for i,r in enumerate(rows[1:],1):seg.extend([0,round(i/FPS,6),float(r[key])])
        curves.append({'Target':'Parameter','Id':param,'Segments':seg})
    write(path,{'Version':3,'Meta':{'Duration':len(rows)/FPS,'Fps':FPS,'Loop':False,'CurveCount':6,
                                 'TotalSegmentCount':(len(rows)-1)*6,'TotalPointCount':len(rows)*6,'AreBeziersRestricted':True},'Curves':curves,'UserData':[]})

def build():
    source=list(csv.DictReader((PREVIOUS/'performance_curve.csv').open(encoding='utf-8-sig')))
    # Keep the accepted speech, head, blink AND breathing timing/values. The
    # local geometry is the only change to the speaking performance.
    rows=[dict(r) for r in source]
    shutil.copy2(PREVIOUS/'performance_curve.csv',OUT/'performance_curve.csv')
    shutil.copy2(PREVIOUS/'N01.wav',OUT/'N01.wav')
    motion(rows,OUT/'performance.motion3.json')
    # Isolate the breathing rig for two four-second cycles, with no speech,
    # head beats or blink; modest 0.15..0.85 parameter span, seamless endpoint.
    idle=[]
    for i in range(241):
        value=.5-.35*math.cos(2*math.pi*i/FPS/4)
        idle.append(dict(mouth_open_y=0,mouth_form=0,eye_l_open=1,eye_r_open=1,breath=value,angle_z=0))
    motion(idle,OUT/'breath_only.motion3.json')
    model=json.loads(MODEL.read_text(encoding='utf-8'))
    model['FileReferences']['Motions']={'Performance':[{'File':'performance.motion3.json','Sound':'N01.wav','FadeInTime':0,'FadeOutTime':0}],
                                      'BreathOnly':[{'File':'breath_only.motion3.json','FadeInTime':0,'FadeOutTime':0}]}
    write(OUT/'Risa_chest_performance.model3.json',model)
    renderer=Renderer();reports={}
    try:
        for name,group,cases in [('speaking','Performance',rows),('breath_only','BreathOnly',idle)]:
            renderer.load(OUT/'Risa_chest_performance.model3.json')
            ids=renderer.model.GetParamIds();indices=[ids.index(p) for p in CHANNELS]
            renderer.model.StartMotion(group,0,3)
            folder=OUT/name;folder.mkdir(exist_ok=True)
            errors=np.zeros(6);bboxes=[]
            for i,r in enumerate(cases):
                im=renderer.frame(r,dt=0 if i==0 else 1/FPS,motion=True)
                actual=np.array([renderer.model.GetParameterValue(j) for j in indices])
                expected=np.array([float(r[k]) for k in CHANNELS.values()])
                errors=np.maximum(errors,np.abs(actual-expected))
                bboxes.append(im.getbbox())
                composite(im).save(folder/f'{i:05d}.png')
                if i%100==0:print(name,i,'SDK max error',float(errors.max()),flush=True)
            reports[name]={'frames':len(cases),'sdk_max_errors':dict(zip(CHANNELS,map(float,errors))),
                           'head_side_not_clipped':all(b and b[0]>0 and b[1]>0 and b[2]<768 for b in bboxes)}
            assert errors.max()<.003 and reports[name]['head_side_not_clipped'],reports[name]
    finally:renderer.close()
    primary=EXPORTS/'Risa_ModelOnly_ChestBreath_v8.mp4'
    breathing=EXPORTS/'Risa_ModelOnly_BreathOnly_v8.mp4'
    common=['-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-threads','8','-movflags','+faststart']
    ffmpeg(['-framerate',FPS,'-i',OUT/'speaking/%05d.png','-i',OUT/'N01.wav',*common,'-c:a','aac','-b:a','192k','-frames:v',len(rows),'-t',f'{len(rows)/FPS:.9f}',primary])
    ffmpeg(['-framerate',FPS,'-i',OUT/'breath_only/%05d.png',*common,'-an','-frames:v',len(idle),breathing])
    write(OUT/'render_verification.json',reports)
    write(OUT/'manifest.json',{'primary':str(primary),'breath_only':str(breathing),
        'rig':'Chest_Local_Breath (Warp4), 8x9 grid under Breath_Base; only Body_Clothes; ParamBreath keys 0 and 1; Breath_Base scale neutralized to 100 percent.',
        'breathing_geometry':'v7 geometry retained. At ParamBreath=1, one upper-collar interior vertex moves 6 GUI pixels toward the collar center (75 percent viewport), with no added vertical displacement. Lower collar, chest, shoulders and abdomen retained. Top edge and silhouette anchored; original texture unchanged.',
        'speaking_curves_unchanged':sha(PREVIOUS/'performance_curve.csv')==sha(OUT/'performance_curve.csv'),
        'audio_unchanged':sha(PREVIOUS/'N01.wav')==sha(OUT/'N01.wav'),
        'hashes':{p.name:sha(p) for p in [OUT/'Risa_chest_breath.cmo3',OUT/'Risa_chest_breath.moc3',OUT/'Risa_chest_breath.2048/texture_00.png',OUT/'performance.motion3.json',primary,breathing]}})
    print('EXPORTED',primary,breathing,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--calibrate',action='store_true');args=p.parse_args()
    calibration() if args.calibrate else build()

