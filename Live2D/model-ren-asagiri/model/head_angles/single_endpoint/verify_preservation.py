"""Compare actual exported runtimes; does not drive the editor or edit artwork."""
from pathlib import Path
import os, json, hashlib, faulthandler
faulthandler.enable()
faulthandler.dump_traceback_later(60, repeat=False)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import pygame
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import live2d.v3 as live2d
from OpenGL.GL import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE, glFinish

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'preview'
SIZE=(1200,1800)
CROP=(390,0,810,570)
DEFAULTS={'ParamAngleX':0,'ParamAngleY':0,'ParamAngleZ':0,
          'ParamEyeLOpen':1,'ParamEyeROpen':1,'ParamMouthOpenY':0,
          'ParamHairFront':0,'ParamHairSide':0,'ParamHairBack':0}

def main():
    pygame.display.init(); live2d.init()
    pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE,8)
    pygame.display.set_mode(SIZE,pygame.OPENGL|pygame.DOUBLEBUF|pygame.HIDDEN)
    live2d.glInit()
    models=[]
    def load(path):
        # The SDK appends its model directory to references; keep exported
        # relative paths. Core Update below bypasses physics evaluation.
        print('Loading '+str(path),flush=True)
        m=live2d.LAppModel(); m.LoadModelJson(str(path)); m.Resize(*SIZE)
        m.SetAutoBlinkEnable(False); m.SetAutoBreathEnable(False)
        models.append(m)
        return m
    before=load(ROOT/'baseline_runtime/Ren_front.model3.json')
    after=load(ROOT/'runtime/Ren_face_endpoint.model3.json')
    def render(m,params):
        pygame.event.pump()
        for p,v in (DEFAULTS|params).items(): m.SetParameterValue(p,float(v))
        m._model.Update(1/30)
        live2d.clearBuffer(0,0,0,0); m.Draw(); glFinish()
        return np.frombuffer(glReadPixels(0,0,*SIZE,GL_RGBA,GL_UNSIGNED_BYTE),np.uint8).reshape(SIZE[1],SIZE[0],4)[::-1].copy()
    def flatten(raw):
        return np.clip(np.rint(raw[:,:,:3].astype(float)+np.array([238,235,229])*(1-raw[:,:,3:4]/255)),0,255).astype(np.uint8)
    tests=[]
    for y in (-30,-15,0,15,30):
        for name,exp in [('rest',{}),('blink',{'ParamEyeLOpen':0,'ParamEyeROpen':0}),('speech',{'ParamMouthOpenY':.7})]:
            tests.append((f'front_y{y}_{name}',{'ParamAngleY':y}|exp))
    tests.extend([('opposite_endpoint',{'ParamAngleX':30,'ParamAngleY':-30}),
                  ('left_no_nod',{'ParamAngleX':-30}),
                  ('left_up',{'ParamAngleX':-30,'ParamAngleY':30})])
    report={'scope':'Static regression against before_tilted_reference_20260926; not artistic acceptance or motion validation',
            'before_drawables':before.GetDrawableIds(),'after_drawables':after.GetDrawableIds(),'cases':[]}
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    sheet=Image.new('RGB',(840,608*3),(248,246,242))
    for i,(name,params) in enumerate(tests):
        print('Checking '+name,flush=True)
        a,b=render(before,params),render(after,params)
        da=np.abs(a.astype(np.int16)-b.astype(np.int16)); df=np.abs(flatten(a).astype(np.int16)-flatten(b).astype(np.int16))
        report['cases'].append({'name':name,'params':params,'raw_max':int(da.max()),
          'display_max':int(df.max()),'display_pixels_over_2':int(np.count_nonzero(df.max(axis=2)>2))})
        if name in ('front_y-30_rest','front_y0_rest','front_y30_rest'):
            row={'front_y-30_rest':0,'front_y0_rest':1,'front_y30_rest':2}[name]
            for col,raw in enumerate((a,b)):
                tile=Image.fromarray(flatten(raw)).crop(CROP)
                sheet.paste(tile,(col*420,row*608+38))
                ImageDraw.Draw(sheet).text((col*420+8,row*608+8),('Baseline' if col==0 else 'Candidate')+' '+name,font=font,fill='black')
    a,b=render(before,{'ParamAngleX':-30,'ParamAngleY':-30}),render(after,{'ParamAngleX':-30,'ParamAngleY':-30})
    da=np.abs(a.astype(np.int16)-b.astype(np.int16))
    report['edited_endpoint']={'raw_changed_pixels':int(np.count_nonzero(da.max(axis=2)>2)),
                              'body_below_y600_max':int(da[600:].max())}
    for name,raw in [('baseline_endpoint',a),('candidate_endpoint_assembly_unadjusted',b)]:
        Image.fromarray(flatten(raw)).crop(CROP).save(OUT/(name+'.png'))
    report['all_unedited_display_cases_pass']=all(c['display_pixels_over_2']==0 for c in report['cases'])
    report['model_sha256']=hashlib.sha256((ROOT/'Ren_face_endpoint.cmo3').read_bytes()).hexdigest()
    report['moc_sha256']=hashlib.sha256((ROOT/'runtime/Ren_face_endpoint.moc3').read_bytes()).hexdigest()
    (ROOT/'preservation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    sheet.save(OUT/'front_nod_preservation.png')
    print(json.dumps({'pass':report['all_unedited_display_cases_pass'],'drawables':[len(report['before_drawables']),len(report['after_drawables'])],'worst_display':max(c['display_max'] for c in report['cases']),'worst_pixels':max(c['display_pixels_over_2'] for c in report['cases']), 'endpoint':report['edited_endpoint']},indent=2))
    for m in models:m.DestroyRenderer()
    live2d.dispose();pygame.quit()
    faulthandler.cancel_dump_traceback_later()

if __name__=='__main__': main()
