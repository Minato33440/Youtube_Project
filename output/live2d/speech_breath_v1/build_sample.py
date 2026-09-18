"""Speech-timed breath on the unchanged accepted v8 rig; local, reproducible N01 trial."""
from pathlib import Path
import argparse,csv,json,math,re,shutil,subprocess,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).resolve().parent
V8=OUT.parent/'chest_breath_v8'
sys.path.insert(0,str(V8))
from build_preview import Renderer,composite,motion,CHANNELS,EXPORTS,ffmpeg,write,sha
FPS=30
OLD=EXPORTS/'Risa_ModelOnly_ChestBreath_v8.mp4'
NEW=EXPORTS/'Risa_ModelOnly_SpeechBreath_v1.mp4'
COMPARE=EXPORTS/'Risa_SpeechBreath_Compare_v8_v1.mp4'
PROFILE={'silence_db':-40,'silence_min_s':.15,'minimum_candidate_s':.24,
         'alignment_margin_s':.25,'start_guard_s':.03,'end_guard_s':.035,
         'inhale_target_s':.36,'minimum_inhale_frames':5,'floor':.18,
         'peak_base':.48,'peak_per_next_phrase_s':.035,'exhale_per_s':.11,
         'max_exhale_drop':.32,'short_inhale_s':.27,'short_refill_cap':.12,
         'start_pose':'already inhaled; insufficient lead-in for a full inhalation',
         'end_pose':'settle at last exhaled level; no forced collapse to zero',
         'long_idle':'Not exercised by this 16s clip; no generalized idle cycle implemented.',
         'interpretation':'Editorial speech performance, not measured respiratory physiology.'}

def rows(path):
    return list(csv.DictReader(path.open(encoding='utf-8-sig')))

def build_curve():
    source=rows(V8/'performance_curve.csv'); count=len(source)
    align_path=OUT.parent/'voice_sync_v2/alignment/phonemes.json'
    alignment=json.loads(align_path.read_text(encoding='utf-8-sig'))
    write(OUT/'source_alignment.json',alignment)
    write(OUT/'breath_profile.json',PROFILE)
    shutil.copy2(V8/'N01.wav',OUT/'N01.wav')
    proc=subprocess.run(['ffmpeg','-hide_banner','-nostdin','-i',str(OUT/'N01.wav'),'-af',
        f"silencedetect=noise={PROFILE['silence_db']}dB:d={PROFILE['silence_min_s']}",'-f','null','-'],capture_output=True,text=True,check=True)
    (OUT/'silence_detection.log').write_text(proc.stderr,encoding='utf-8')
    starts=[float(x) for x in re.findall(r'silence_start: ([0-9.]+)',proc.stderr)]
    ends=[float(x) for x in re.findall(r'silence_end: ([0-9.]+)',proc.stderr)]
    assert len(starts)==len(ends)
    markers=[p for p in alignment['phonemes'] if p['phoneme'].lower() in {'sp','sil','pau'}]
    last_phone=max(p['end_s'] for p in alignment['phonemes'] if p['phoneme'].lower() not in {'sp','sil','pau'})
    events=[]; rejected=[]
    for a,b in zip(starts,ends):
        evidence=[p for p in markers if p['start_s']<=b+.25 and p['end_s']>=a-.25]
        reason=None
        if b-a<PROFILE['minimum_candidate_s']:reason='too short'
        elif a>=last_phone-.03:reason='trailing silence; no next phrase'
        elif not evidence:reason='no aligned phrase-pause evidence; possible voiceless speech'
        if reason:
            rejected.append({'start_s':a,'end_s':b,'reason':reason});continue
        end=min(count-1,math.floor((b-PROFILE['end_guard_s'])*FPS))
        start=max(math.ceil((a+PROFILE['start_guard_s'])*FPS),end-round(PROFILE['inhale_target_s']*FPS))
        if end-start<PROFILE['minimum_inhale_frames']:
            rejected.append({'start_s':a,'end_s':b,'reason':'too few guarded frames'});continue
        events.append({'silence_start_s':a,'silence_end_s':b,'start_frame':start,'end_frame':end,
                       'start_s':start/FPS,'end_s':end/FPS,'inhale_duration_s':(end-start)/FPS,
                       'pause_evidence':[{'start_s':p['start_s'],'end_s':p['end_s'],'mora':p['mora'],'sentence':p['sentence']} for p in evidence]})
    ceiling=max(float(r['breath']) for r in source)
    values=np.zeros(count); first=min(p['start_s'] for p in alignment['phonemes'])
    def peak(seconds):return min(ceiling,PROFILE['peak_base']+PROFILE['peak_per_next_phrase_s']*seconds)
    def segment(a,b,lo,hi):
        x=np.linspace(0,1,b-a+1); smooth=x*x*(3-2*x)
        values[a:b+1]=lo+(hi-lo)*smooth
    cursor=math.ceil(first*FPS); level=peak(events[0]['start_s']-first)
    values[:cursor+1]=level
    exhalations=[]
    for j,event in enumerate(events):
        start,end=event['start_frame'],event['end_frame']
        duration=(start-cursor)/FPS
        valley=max(PROFILE['floor'],level-min(PROFILE['max_exhale_drop'],PROFILE['exhale_per_s']*duration))
        segment(cursor,start,level,valley)
        exhalations.append({'start_frame':cursor,'end_frame':start,'from':level,'to':valley})
        next_start=events[j+1]['start_frame'] if j+1<len(events) else min(count-1,math.ceil(last_phone*FPS))
        target=peak((next_start-end)/FPS)
        if event['inhale_duration_s']<PROFILE['short_inhale_s']:target=min(target,valley+PROFILE['short_refill_cap'])
        target=max(valley,target)
        segment(start,end,valley,target)
        event.update({'from':valley,'to':target,'next_phrase_span_s':(next_start-end)/FPS})
        cursor,level=end,target
    end=min(count-1,math.ceil(last_phone*FPS))
    valley=max(PROFILE['floor'],level-min(PROFILE['max_exhale_drop'],PROFILE['exhale_per_s']*(end-cursor)/FPS))
    segment(cursor,end,level,valley);values[end:]=valley
    exhalations.append({'start_frame':cursor,'end_frame':end,'from':level,'to':valley})
    output=[{**r,'breath':f'{values[i]:.6f}'} for i,r in enumerate(source)]
    with (OUT/'performance_curve.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(source[0]));w.writeheader();w.writerows(output)
    motion(output,OUT/'performance.motion3.json')
    write(OUT/'breath_events.json',{'inhales':events,'exhalations':exhalations,'skipped_silences':rejected,
        'source_silences':list(zip(starts,ends)),'first_phone_s':first,'last_phone_s':last_phone,
        'v8_peak_ceiling':ceiling,'initial_value':float(values[0]),'final_value':float(values[-1])})
    folder=OUT/'model';folder.mkdir(exist_ok=True)
    files=['Risa_chest_breath.cmo3','Risa_chest_breath.moc3','Risa_chest_breath.cdi3.json','Risa_chest_breath.2048/texture_00.png']
    for name in files:
        target=folder/name;target.parent.mkdir(exist_ok=True);shutil.copy2(V8/name,target)
    model=json.loads((V8/'Risa_chest_breath.model3.json').read_text(encoding='utf-8'))
    model['FileReferences']['Motions']={'Performance':[{'File':'../performance.motion3.json','Sound':'../N01.wav','FadeInTime':0,'FadeOutTime':0}]}
    write(folder/'Risa_speech_breath.model3.json',model)
    write(OUT/'source_hashes.json',{str(p.relative_to(OUT.parent)):sha(p) for p in [V8/'performance_curve.csv',V8/'N01.wav',align_path,V8/'build_preview.py',*[V8/n for n in files]]})
    # Standalone visual trace: orange old breath, green new breath; blue pause windows.
    plot=Image.new('RGB',(1600,460),'white');d=ImageDraw.Draw(plot);font=ImageFont.load_default(size=20)
    x=lambda t:70+t/((count-1)/FPS)*1480
    y=lambda b:380-b/.65*280
    for event in events:d.rectangle((x(event['start_s']),80,x(event['end_s']),380),fill='#e1efff')
    for val in [0,.2,.4,.6]:
        d.line((70,y(val),1550,y(val)),fill='#dddddd');d.text((10,y(val)-10),str(val),fill='black',font=font)
    for t in range(17):d.text((x(t)-5,395),str(t),fill='black',font=font)
    for data,color in [(np.array([float(r['breath']) for r in source]),'#d17a20'),(values,'#16845b')]:
        d.line([(x(i/FPS),y(v)) for i,v in enumerate(data)],fill=color,width=3)
    d.text((70,20),'ORANGE: v8 periodic / GREEN: speech breath / BLUE: inhale windows',fill='black',font=font)
    plot.save(OUT/'breath_timing.png')
    print(json.dumps({'inhales':events,'skipped':rejected,'range':[min(values),max(values)]},ensure_ascii=True,indent=2))

def render():
    cases=rows(OUT/'performance_curve.csv');folder=OUT/'speaking';folder.mkdir(exist_ok=True)
    renderer=Renderer();errors=np.zeros(6)
    try:
        renderer.load(OUT/'model/Risa_speech_breath.model3.json')
        ids=renderer.model.GetParamIds();indices=[ids.index(p) for p in CHANNELS]
        renderer.model.StartMotion('Performance',0,3)
        for i,r in enumerate(cases):
            im=renderer.frame(r,dt=0 if i==0 else 1/FPS,motion=True)
            actual=np.array([renderer.model.GetParameterValue(j) for j in indices])
            errors=np.maximum(errors,np.abs(actual-np.array([float(r[k]) for k in CHANNELS.values()])))
            assert im.getbbox()[0]>0 and im.getbbox()[1]>0 and im.getbbox()[2]<768
            composite(im).save(folder/f'{i:05d}.png')
            if i%100==0:print('frame',i,'error',float(errors.max()),flush=True)
    finally:renderer.close()
    assert errors.max()<.003,errors
    ffmpeg(['-framerate',30,'-i',folder/'%05d.png','-i',OLD,'-map','0:v','-map','1:a:0','-c:v','libx264','-preset','medium','-crf',18,'-pix_fmt','yuv420p','-threads',8,'-c:a','copy','-frames:v',len(cases),'-movflags','+faststart',NEW])
    header=Image.new('RGB',(1920,70),'#18202c');d=ImageDraw.Draw(header);font=ImageFont.load_default(size=30)
    d.text((30,20),'A: v8 PERIODIC',font=font,fill='white');d.text((990,20),'B: SPEECH-TIMED BREATH',font=font,fill='white')
    header.save(OUT/'comparison_header.png')
    ffmpeg(['-i',OLD,'-i',NEW,'-loop',1,'-framerate',30,'-i',OUT/'comparison_header.png','-filter_complex',
        '[0:v]crop=660:660:210:210,scale=960:960,setpts=PTS-STARTPTS[a];[1:v]crop=660:660:210:210,scale=960:960,setpts=PTS-STARTPTS[b];[a][b]hstack[body];[2:v][body]vstack[v]',
        '-map','[v]','-map','0:a:0','-frames:v',len(cases),'-r',30,'-c:v','libx264','-crf',18,'-preset','medium','-threads',8,'-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',COMPARE])
    write(OUT/'render_verification.json',{'sdk_max_errors':dict(zip(CHANNELS,map(float,errors))),'frames':len(cases),'passed':True})
    write(OUT/'manifest.json',{'model_geometry':'Unchanged v8; byte-identical cmo3, moc3 and texture','changed_channel':'ParamBreath only','primary':str(NEW),'comparison':str(COMPARE),
        'hashes':{str(p.relative_to(OUT)) if p.is_relative_to(OUT) else str(p):sha(p) for p in [OUT/'performance_curve.csv',OUT/'performance.motion3.json',NEW,COMPARE]}})
    print('EXPORTED',NEW,COMPARE)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--curve-only',action='store_true');p.add_argument('--render-only',action='store_true');args=p.parse_args()
    if not args.render_only:build_curve()
    if not args.curve_only:render()
