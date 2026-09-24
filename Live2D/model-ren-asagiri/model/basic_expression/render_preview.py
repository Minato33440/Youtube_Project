"""Render the exported Cubism rig itself; never modify source artwork."""
from pathlib import Path
import os, json, math, hashlib, subprocess, argparse
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import pygame
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import live2d.v3 as live2d
from OpenGL.GL import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE, glFinish

ROOT=Path(__file__).resolve().parent
MODEL=ROOT/'runtime/Ren_front.model3.json'
OUT=ROOT/'preview'
SIZE=(1200,1800)
FPS=30
PARAMS=['ParamEyeLOpen','ParamEyeROpen','ParamMouthOpenY']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--probe',action='store_true');args=parser.parse_args()
    OUT.mkdir(exist_ok=True)
    print('INIT',flush=True)
    pygame.display.init();live2d.init()
    pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE,8)
    pygame.display.set_mode(SIZE,pygame.OPENGL|pygame.DOUBLEBUF|pygame.HIDDEN)
    live2d.glInit()
    print('LOAD',MODEL,flush=True)
    model=live2d.LAppModel();model.LoadModelJson(str(MODEL));model.Resize(*SIZE)
    print('LOADED',flush=True)
    model.SetAutoBlinkEnable(False);model.SetAutoBreathEnable(False)
    ids=model.GetParamIds(); indices=[ids.index(p) for p in PARAMS]
    report={'model':str(MODEL),'parameter_ids':ids,'cases':[],'source':'Actual exported moc3 rendered with Live2D runtime'}
    def render(vals):
        pygame.event.pump()
        for p,v in zip(PARAMS,vals): model.SetParameterValue(p,float(v))
        model._model.Update(1/FPS)
        actual=[float(model.GetParameterValue(i)) for i in indices]
        assert max(abs(a-b) for a,b in zip(actual,vals))<0.0001,(actual,vals)
        live2d.clearBuffer(0,0,0,0);model.Draw();glFinish()
        pix=glReadPixels(0,0,*SIZE,GL_RGBA,GL_UNSIGNED_BYTE)
        rgba=np.frombuffer(pix,np.uint8).reshape(SIZE[1],SIZE[0],4).copy()
        alpha=rgba[:,:,3:4].astype(np.float32)
        rgba[:,:,:3]=np.clip(np.rint(rgba[:,:,:3].astype(np.float32)*255/np.maximum(alpha,1)),0,255).astype(np.uint8)
        return Image.fromarray(rgba).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    def on_bg(im):
        bg=Image.new('RGBA',im.size,(234,228,218,255));bg.alpha_composite(im);return bg.convert('RGB')
    try:
        neutral=render((1,1,0));neutral.save(OUT/'neutral_full.png')
        on_bg(neutral).save(OUT/'neutral_full.jpg',quality=95)
        print('NEUTRAL_BBOX',neutral.getbbox(),flush=True)
        if args.probe: return
        crop=(420,0,780,480)
        def tile(im,label):
            im=on_bg(im.crop(crop)).resize((480,640),Image.Resampling.LANCZOS)
            result=Image.new('RGB',(480,678),(244,241,236));result.paste(im,(0,38))
            ImageDraw.Draw(result).text((12,10),label,fill=(30,35,43),font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18))
            return result
        cases=[('Open',1,1,0),('Eyes 0.75',.75,.75,0),('Eyes 0.50',.5,.5,0),('Eyes 0.25',.25,.25,0),('Closed',0,0,0),('Left blink',0,1,0),('Right blink',1,0,0),('Mouth 0.10',1,1,.1),('Mouth 0.25',1,1,.25),('Mouth 0.50',1,1,.5),('Mouth 0.75',1,1,.75),('Mouth 1.00',1,1,1)]
        sheet=Image.new('RGB',(480*4,678*3),(244,241,236))
        for i,(label,*vals) in enumerate(cases):
            im=render(vals);im.crop(crop).save(OUT/f'case_{i:02d}.png')
            sheet.paste(tile(im,label),(i%4*480,i//4*678))
            report['cases'].append({'label':label,'values':dict(zip(PARAMS,vals)),'alpha_bbox':im.getbbox()})
        sheet.save(OUT/'expression_review.jpg',quality=95)
        frames=[];curve=[]
        ff=subprocess.Popen(['ffmpeg','-y','-nostdin','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','480x678','-r',str(FPS),'-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'Ren_blink_mouth.mp4')],stdin=subprocess.PIPE)
        for f in range(FPS*10):
            t=f/FPS
            def blink(center,duration=.36): return min(1.,abs(t-center)/(duration/2))
            eye=min(blink(1),blink(2.5,.8),blink(8.7))
            left=eye if not 3.3<t<3.9 else blink(3.6,.5)
            right=eye if not 4.1<t<4.7 else blink(4.4,.5)
            mouth=(.5-.5*math.cos(2*math.pi*(t-5)/2)) if 5<=t<=9 else 0.
            vals=[left,right,mouth]
            frame=tile(render(vals),f'Eye L {left:.2f} / R {right:.2f}    Mouth {mouth:.2f}')
            ff.stdin.write(frame.tobytes())
            if f%2==0:frames.append(frame)
            curve.append(vals)
        ff.stdin.close();assert ff.wait()==0
        frames[0].save(OUT/'Ren_blink_mouth.gif',save_all=True,append_images=frames[1:],duration=[67,67,66]*50,loop=0)
        report.update(frames=300,fps=FPS,duration_seconds=10,parameter_max_error_below=0.0001)
        (OUT/'parameter_curve.json').write_text(json.dumps(curve),encoding='utf-8')
        report['runtime_hashes']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'runtime').rglob('*') if p.is_file()}
        (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('PREVIEW_COMPLETE',OUT,flush=True)
    finally:
        model.DestroyRenderer();live2d.dispose();pygame.quit()

if __name__=='__main__':main()
