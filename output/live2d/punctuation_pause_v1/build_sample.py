"""Retain voiced PCM, edit verified pauses, retime performance, render native v8 rig."""
from pathlib import Path
import csv,json,math,shutil,subprocess,sys,wave
import numpy as np
from PIL import Image,ImageDraw
OUT=Path(__file__).resolve().parent
SRC=OUT.parent/'speech_breath_v1'
sys.path.insert(0,str(OUT.parent/'chest_breath_v8'))
from build_preview import Renderer,composite,motion,CHANNELS,EXPORTS,ffmpeg,write,sha
FPS=30
NEW=EXPORTS/'Risa_ModelOnly_PunctuationPause_v1.mp4'
PROFILE={'comma_s':.12,'period_s':.50,'question_s':.70,'implicit_clause_pause_s':.12,
         'inhale_s':.36,'breath_floor':.18,'breath_peak':.593756,
         'note':'Total measured gap, not added silence. Local narration editing preset; not an Aivis engine default.'}

def main():
    source=list(csv.DictReader((SRC/'performance_curve.csv').open(encoding='utf-8-sig')))
    with wave.open(str(SRC/'N01.wav'),'rb') as w:
        sr=w.getframerate();channels=w.getnchannels();assert w.getsampwidth()==2
        audio=np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,channels).copy()
    # Pauses verified by -40 dB silence detection AND phoneme/punctuation alignment.
    candidates=[(.959562,1.395729,'comma',.12),(2.5695,2.864479,'question',.70),
        (3.924646,4.384854,'comma',.12),(5.345083,5.827937,'implicit_clause',.12),
        (8.273062,8.541604,'period',.50),(9.644937,10.100146,'comma',.12),
        (12.101167,12.553417,'comma',.12),(13.827646,14.115062,'question',.70)]
    pieces=[]; edits=[]; cursor=0; output_samples=0; segments=[]
    def keep(a,b):
        nonlocal output_samples
        pieces.append(audio[a:b]);segments.append({'old_start':a,'old_end':b,'new_start':output_samples,'new_end':output_samples+b-a})
        output_samples+=b-a
    for a,b,kind,target in candidates:
        start,end=round(a*sr),round(b*sr);old=end-start;desired=round(target*sr)
        new_start=start+(output_samples-cursor)
        if desired<old:
            # Retain both 60ms edges so low-level consonant tails/onsets are not removed.
            left=start+desired//2;right=end-(desired-desired//2)
            removed=audio[left:right]
            assert np.abs(removed.astype(int)).max()<328,'not a silent center'
            keep(cursor,left)
            segments.append({'old_start':left,'old_end':right,'new_start':output_samples,'new_end':output_samples})
            cursor=right
            # Smooth only 2ms of low-level pause PCM around the join, never speech.
            n=round(.002*sr)
            pieces[-1]=pieces[-1].copy()
            pieces[-1][-n:]=np.rint(pieces[-1][-n:]*np.linspace(1,0,n)[:,None]).astype('<i2')
        else:
            center=(start+end)//2;keep(cursor,center)
            added=desired-old;pieces.append(np.zeros((added,channels),dtype='<i2'))
            segments.append({'old_start':center,'old_end':center,'new_start':output_samples,'new_end':output_samples+added})
            output_samples+=added;cursor=center
        edits.append({'kind':kind,'old_start_s':start/sr,'old_end_s':end/sr,'new_start_s':new_start/sr,
                      'new_end_s':(new_start+desired)/sr,'target_s':target,'delta_s':(desired-old)/sr})
    keep(cursor,len(audio));new_audio=np.concatenate(pieces)
    # De-click retained pause edges after each insertion/removal. Still inside verified silence.
    for e in edits:
        c=round((e['new_start_s']+e['target_s']/2)*sr);n=round(.002*sr)
        if e['delta_s']<0:
            new_audio[c:c+n]=np.rint(new_audio[c:c+n]*np.linspace(0,1,n)[:,None]).astype('<i2')
        else:
            half=round((e['old_end_s']-e['old_start_s'])*sr/2)
            left=round(e['new_start_s']*sr)+half;right=left+round(e['delta_s']*sr)
            new_audio[left-n:left]=np.rint(new_audio[left-n:left]*np.linspace(1,0,n)[:,None]).astype('<i2')
            new_audio[right:right+n]=np.rint(new_audio[right:right+n]*np.linspace(0,1,n)[:,None]).astype('<i2')
    count=math.ceil(len(new_audio)/sr*FPS);padding=round(count/FPS*sr)-len(new_audio)
    new_audio=np.concatenate([new_audio,np.zeros((padding,channels),dtype='<i2')])
    with wave.open(str(OUT/'N01.wav'),'wb') as w:
        w.setparams((channels,2,sr,0,'NONE','not compressed'));w.writeframes(new_audio.astype('<i2').tobytes())
    def forward(t):
        shift=0
        for e in edits:
            a,b=e['old_start_s'],e['old_end_s']
            if t>=b:shift+=e['delta_s']
            elif t>a:return e['new_start_s']+(t-a)/(b-a)*e['target_s']
            else:break
        return t+shift
    def inverse(t):
        shift=0
        for e in edits:
            a,b=e['new_start_s'],e['new_end_s']
            if t>=b:shift+=e['delta_s']
            elif t>a:return e['old_start_s']+(t-a)/(b-a)*(e['old_end_s']-e['old_start_s'])
            else:break
        return t-shift
    times=np.arange(count)/FPS;old_times=np.array([inverse(t) for t in times]);old_grid=np.arange(len(source))/FPS
    curves={k:np.interp(old_times,old_grid,[float(r[k]) for r in source]) for k in CHANNELS.values()}
    # Preserve blink durations: only move each blink's center; do not squeeze a blink with a comma.
    blink_events=[]
    for key in ['eye_l_open','eye_r_open']:
        vals=np.array([float(r[key]) for r in source]);active=vals<.999
        bounds=np.flatnonzero(np.diff(np.r_[False,active,False].astype(int))).reshape(-1,2)
        curves[key]=np.ones(count)
        for a,b in bounds:
            a=max(0,a-1);b=min(len(vals)-1,b);center=(a+b)/2/FPS;new_center=forward(center)
            shape=np.interp(times-new_center,old_grid[a:b+1]-center,vals[a:b+1],left=1,right=1)
            curves[key]=np.minimum(curves[key],shape)
            blink_events.append({'eye':key,'old_center_s':center,'new_center_s':new_center,'duration_s':(b-a)/FPS})
    # Speech breathing: short commas do not trigger inhalation; only sentence boundaries do.
    breath=np.zeros(count);cursor=0;level=PROFILE['breath_peak'];inhales=[]
    def curve(a,b,lo,hi):
        x=np.linspace(0,1,b-a+1);breath[a:b+1]=lo+(hi-lo)*x*x*(3-2*x)
    for e in edits:
        if e['kind'] not in ['period','question']:continue
        end=math.floor((e['new_end_s']-.05)*FPS);start=end-round(.36*FPS)
        assert start/FPS>=e['new_start_s']+.03
        valley=max(.18,level-min(.36,.11*(start-cursor)/FPS))
        curve(cursor,start,level,valley);curve(start,end,valley,PROFILE['breath_peak'])
        inhales.append({'start_frame':start,'end_frame':end,'start_s':start/FPS,'end_s':end/FPS,'from':valley,'to':PROFILE['breath_peak']})
        cursor=end;level=PROFILE['breath_peak']
    last=math.ceil(forward(15.544375)*FPS)
    valley=max(.18,level-min(.36,.11*(last-cursor)/FPS));curve(cursor,last,level,valley);breath[last:]=valley
    curves['breath']=breath
    rows=[]
    for i,t in enumerate(times):
        old=source[min(len(source)-1,max(0,round(old_times[i]*FPS)))];r={**old,'frame':i,'time_s':f'{t:.6f}'}
        r.update({k:f'{v[i]:.6f}' for k,v in curves.items()});rows.append(r)
    with (OUT/'performance_curve.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    motion(rows,OUT/'performance.motion3.json')
    shutil.copytree(SRC/'model',OUT/'model',dirs_exist_ok=True)
    write(OUT/'pause_profile.json',PROFILE)
    write(OUT/'time_map.json',{'sample_rate':sr,'source_duration_s':len(audio)/sr,'duration_s':len(new_audio)/sr,
          'edits':edits,'pcm_segments':segments,'padding_samples':padding,'mapping_note':'Motion inside edited pauses is interpolated; all outside pause intervals has exact translated source time.'})
    write(OUT/'breath_events.json',{'inhales':inhales,'blink_events':blink_events})
    alignment=json.loads((SRC/'source_alignment.json').read_text(encoding='utf-8-sig'))
    for p in alignment['phonemes']:
        p['original_start_s']=p['start_s'];p['original_end_s']=p['end_s']
        p['start_s']=forward(p['start_s']);p['end_s']=forward(p['end_s'])
    alignment['retiming_note']='Existing alignment transported through pause map, not newly forced-aligned. Original source/concat fields retained for provenance.'
    write(OUT/'retimed_alignment.json',alignment)
    renderer=Renderer();errors=np.zeros(6);thumbs=[]
    pipe=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1080','-r','30','-i','-',
          '-i',str(OUT/'N01.wav'),'-map','0:v','-map','1:a','-c:v','libx264','-crf','18','-preset','medium','-threads','8',
          '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(NEW)],stdin=subprocess.PIPE)
    try:
        renderer.load(OUT/'model/Risa_speech_breath.model3.json');ids=renderer.model.GetParamIds();indices=[ids.index(p) for p in CHANNELS]
        renderer.model.StartMotion('Performance',0,3)
        for i,r in enumerate(rows):
            im=renderer.frame(r,dt=0 if i==0 else 1/FPS,motion=True)
            actual=np.array([renderer.model.GetParameterValue(j) for j in indices])
            errors=np.maximum(errors,np.abs(actual-np.array([float(r[k]) for k in CHANNELS.values()])))
            assert im.getbbox()[0]>0 and im.getbbox()[1]>0 and im.getbbox()[2]<768
            rgb=composite(im);pipe.stdin.write(rgb.tobytes())
            if i%60==0:thumbs.append((i,rgb.resize((270,270))));print('frame',i,flush=True)
        pipe.stdin.close();assert pipe.wait()==0
    finally:renderer.close()
    assert errors.max()<.003,errors
    sheet=Image.new('RGB',(1080,600),'white');d=ImageDraw.Draw(sheet)
    for j,(i,im) in enumerate(thumbs):x=j%4*270;y=j//4*300;sheet.paste(im,(x,y));d.text((x+5,y+275),f'{i/FPS:.2f}s',fill='black')
    sheet.save(OUT/'visual_review.jpg')
    write(OUT/'render_verification.json',{'sdk_max_error':float(errors.max()),'frames':count,'video':str(NEW)})
    write(OUT/'source_hashes.json',{str(p):sha(p) for p in [SRC/'N01.wav',SRC/'performance_curve.csv',SRC/'source_alignment.json']})
    print('DONE',NEW,count/FPS,flush=True)

if __name__=='__main__':main()
