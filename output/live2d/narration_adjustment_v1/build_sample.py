"""Generate a separately versioned N01 sample using the existing Risa rig."""
from pathlib import Path
import csv, hashlib, json, os, shutil, subprocess, time
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SOURCE = OUT.parent / 'full_sample_v1/N01'
RIG = OUT.parent / 'voice_sync_v4/model'
PROJECT = ROOT / 'Politics_Economics/2026-09-09_fiscal_policy'
MEDIA = PROJECT / 'media/sample_v1_risa'
EXPORT = PROJECT / 'exports/Risa_Narration_N01_SizeMotion_Adjusted_v1.mp4'
CHANNELS = {'ParamMouthOpenY':'mouth_open_y','ParamMouthForm':'mouth_form',
            'ParamEyeLOpen':'eye_l_open','ParamEyeROpen':'eye_r_open',
            'ParamBreath':'breath','ParamAngleZ':'angle_z'}
FPS, COUNT = 30, 479

def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ffmpeg(args):
    subprocess.run(['ffmpeg','-v','error','-nostdin','-y', *map(str,args)],check=True)

def build():
    before = list(csv.DictReader((SOURCE/'performance_curve.csv').open(encoding='utf-8-sig')))
    assert len(before) == COUNT
    rows = []
    for old in before:
        r = dict(old)
        r['mouth_open_y'] = f"{min(1., float(old['mouth_open_y'])*1.2):.6f}"
        form = float(old['mouth_form'])
        r['mouth_form'] = f"{form*(.55 if form<0 else 1.):.6f}"
        r['angle_z'] = f"{float(old['angle_z'])*2.:.6f}"
        rows.append(r)
    with (OUT/'performance_curve.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    motion=json.loads((SOURCE/'performance.motion3.json').read_text(encoding='utf-8'))
    for curve in motion['Curves']:
        vals=[float(r[CHANNELS[curve['Id']]]) for r in rows]
        segments=[0., vals[0]]
        for i,v in enumerate(vals[1:],1): segments += [0,round(i/FPS,6),v]
        curve['Segments']=segments
    write_json(OUT/'performance.motion3.json',motion)
    (OUT/'model').mkdir(exist_ok=True)
    model=json.loads((RIG/'Risa_mouth_shapes.model3.json').read_text(encoding='utf-8'))
    refs=model['FileReferences']
    refs['Moc']='../../voice_sync_v4/model/'+refs['Moc']
    refs['Textures']=['../../voice_sync_v4/model/'+t for t in refs['Textures']]
    refs['DisplayInfo']='../../voice_sync_v4/model/'+refs['DisplayInfo']
    refs['Motions']={'Adjusted':[{'File':'../performance.motion3.json','Sound':'../N01.wav','FadeInTime':0,'FadeOutTime':0}]}
    write_json(OUT/'model/Risa_adjusted.model3.json',model)
    shutil.copy2(MEDIA/'audio/N01.wav',OUT/'N01.wav')
    profile={'source_curve':str(SOURCE/'performance_curve.csv'),'fps':FPS,'frames':COUNT,
             'mouth_open_multiplier':1.2,'negative_mouth_form_multiplier':.55,
             'positive_mouth_form_multiplier':1.,'neck_multiplier':2.,
             'timing_blink_breath':'preserved exactly from N01',
             'layout':{'scale_relative_to_previous':1.5,'overlay_xy':[1180,70],
                       'overlay_wh':[576,450],'render_canvas':[1152,1536],
                       'render_crop_xywh':[192,0,768,600],
                       'note':'Bust crop; bottom at y=520, above cards beginning at y=545.'},
             'rig_geometry':'unchanged; calibrated animation values remain within existing parameter limits',
             'editor_model':str(OUT.parent/'voice_sync_v4/Risa_coordinated.cmo3'),
             'model_scope':'model3 references existing rig assets; this folder alone is not a standalone model package'}
    write_json(OUT/'adjustment_profile.json',profile)
    return before,rows

def render(rows):
    import pygame
    import live2d.v3 as live2d
    from OpenGL.GL import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE, glFinish
    pygame.display.init(); live2d.init()
    pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE,8)
    size=(1152,1536)
    pygame.display.set_mode(size,pygame.OPENGL|pygame.DOUBLEBUF|pygame.HIDDEN)
    live2d.glInit()
    model=live2d.LAppModel(); model.LoadModelJson(str(OUT/'model/Risa_adjusted.model3.json'))
    model.Resize(*size); model.SetAutoBlinkEnable(False); model.SetAutoBreathEnable(False)
    ids=model.GetParamIds(); indices=[ids.index(k) for k in CHANNELS]
    model.StartMotion('Adjusted',0,3)
    frames=OUT/'frames'; frames.mkdir(exist_ok=True)
    errors=np.zeros(6); bboxes=[]
    for i,r in enumerate(rows):
        pygame.event.pump(); model._model.Update(0 if i==0 else 1/FPS)
        actual=np.array([model.GetParameterValue(j) for j in indices])
        expected=np.array([float(r[k]) for k in CHANNELS.values()])
        errors=np.maximum(errors,np.abs(actual-expected))
        live2d.clearBuffer(0,0,0,0); model.Draw(); glFinish()
        pixels=glReadPixels(0,0,*size,GL_RGBA,GL_UNSIGNED_BYTE)
        rgba=np.frombuffer(pixels,dtype=np.uint8).reshape(size[1],size[0],4).copy()
        a=rgba[:,:,3:4].astype(np.float32)
        rgba[:,:,:3]=np.clip(np.rint(rgba[:,:,:3].astype(np.float32)*255/np.maximum(a,1)),0,255).astype(np.uint8)
        im=Image.fromarray(rgba).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        crop=im.crop((192,0,960,600))
        bboxes.append(crop.getbbox())
        crop.save(frames/f'{i:05d}.png')
        if i%100==0: print('render frame',i,'max SDK error',float(errors.max()),flush=True)
    model.DestroyRenderer(); del model; live2d.dispose(); pygame.quit()
    report={'passed':bool(errors.max()<.003),'tolerance':.003,'frames':COUNT,
            'max_absolute_parameter_error':dict(zip(CHANNELS,map(float,errors))),
            'render_path':'Actual SDK motion3 playback with automatic blink/breath disabled',
            'all_frames_have_model':all(b is not None for b in bboxes),
            'no_head_or_side_clipping':all(b and b[0]>0 and b[1]>0 and b[2]<768 for b in bboxes),
            'bottom_cropping':'intentional bust crop'}
    write_json(OUT/'sdk_render_verification.json',report)
    assert report['passed'] and report['all_frames_have_model'] and report['no_head_or_side_clipping'],report

def compose():
    ffmpeg(['-i',MEDIA/'backgrounds/N01.mp4','-framerate',FPS,'-i',OUT/'frames/%05d.png',
            '-i',OUT/'N01.wav','-filter_complex_threads','2','-filter_complex',
            '[0:v]settb=1/30,setpts=N[bg];[1:v]scale=576:450:flags=lanczos,format=rgba,settb=1/30,setpts=N[model];[bg][model]overlay=1180:70:shortest=1:format=auto[v]',
            '-map','[v]','-map','2:a:0','-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p',
            '-threads','8','-frames:v',COUNT,'-c:a','aac','-b:a','192k','-ar','48000','-t',f'{COUNT/FPS:.9f}',
            '-movflags','+faststart',EXPORT])

def main():
    started=time.time(); before,rows=build(); render(rows); compose()
    write_json(OUT/'manifest.json',{'export':str(EXPORT),'frames':COUNT,'fps':FPS,'duration_s':COUNT/FPS,
        'input_hashes':{str(p):sha(p) for p in [SOURCE/'performance_curve.csv',SOURCE/'performance.motion3.json',
            RIG/'Risa_mouth_shapes.moc3',RIG/'Risa_mouth_shapes.2048/texture_00.png',MEDIA/'audio/N01.wav',MEDIA/'backgrounds/N01.mp4']},
        'output_hashes':{str(p):sha(p) for p in [OUT/'performance_curve.csv',OUT/'performance.motion3.json',EXPORT]},
        'elapsed_seconds':round(time.time()-started,2),'original_assets_modified':False})
    print('EXPORTED',EXPORT,flush=True)

if __name__=='__main__': main()
