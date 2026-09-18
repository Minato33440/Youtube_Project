"""Verify actual pause containment, unchanged non-breath channels, SDK video and audio."""
import json,subprocess
import numpy as np
from PIL import Image,ImageDraw
from build_sample import OUT,V8,OLD,NEW,COMPARE,FPS,rows,sha,write

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(path)]))['streams']

def frame(path,index,w,h):
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf',f'select=eq(n\\,{index})','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
    return np.frombuffer(raw,np.uint8).reshape(h,w,3)

def pcm(path):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ac','1','-ar','48000','-f','f32le','-'])

def main():
    old,new=rows(V8/'performance_curve.csv'),rows(OUT/'performance_curve.csv')
    assert len(old)==len(new)==479
    assert all(all(a[k]==b[k] for k in a if k!='breath') for a,b in zip(old,new))
    for name in ['Risa_chest_breath.cmo3','Risa_chest_breath.moc3','Risa_chest_breath.cdi3.json','Risa_chest_breath.2048/texture_00.png']:
        assert sha(V8/name)==sha(OUT/'model'/name)
    assert sha(V8/'N01.wav')==sha(OUT/'N01.wav')
    ev=json.loads((OUT/'breath_events.json').read_text(encoding='utf-8'))
    profile=json.loads((OUT/'breath_profile.json').read_text(encoding='utf-8'))
    b=np.array([float(r['breath']) for r in new]);delta=np.diff(b)
    allowed=np.zeros(len(delta),dtype=bool); inhale_checks=[]
    audio=np.frombuffer(pcm(OUT/'N01.wav'),'<f4')
    for e in ev['inhales']:
        a,z=e['start_frame'],e['end_frame'];allowed[a:z]=True
        assert a/FPS>=e['silence_start_s']+profile['start_guard_s']-1e-6
        assert z/FPS<=e['silence_end_s']-profile['end_guard_s']+1e-6
        assert np.all(delta[a:z]>=-1e-6) and b[z]-b[a]>.05
        peak=float(np.abs(audio[round(a/FPS*48000):round(z/FPS*48000)]).max())
        assert peak<10**(profile['silence_db']/20)+1e-5,peak
        inhale_checks.append({'start_s':a/FPS,'end_s':z/FPS,'gain':float(b[z]-b[a]),'audio_peak_dbfs':float(20*np.log10(max(peak,1e-12)))})
    assert not np.any(delta[~allowed]>1e-6),'inhaling outside a verified pause'
    assert min(b)>=profile['floor'] and max(b)<=ev['v8_peak_ceiling']+1e-6
    assert max(np.abs(delta))<.05, 'abrupt one-frame parameter change'
    exhale_rates=[]
    for e in ev['exhalations']:
        a,z=e['start_frame'],e['end_frame'];assert np.all(delta[a:z]<=1e-6)
        exhale_rates.append(float((b[a]-b[z])/((z-a)/FPS)))
    inhale_rates=[e['gain']/(e['end_s']-e['start_s']) for e in inhale_checks]
    assert min(inhale_rates)>max(exhale_rates)
    # The other five curves remain byte-for-byte identical inside motion JSON.
    om=json.loads((V8/'performance.motion3.json').read_text(encoding='utf-8'))
    nm=json.loads((OUT/'performance.motion3.json').read_text(encoding='utf-8'))
    assert [c for c in om['Curves'] if c['Id']!='ParamBreath']==[c for c in nm['Curves'] if c['Id']!='ParamBreath']
    indices=[0,30,40,162,173,291,301,416,422,478]
    encoded_audio=pcm(OLD)
    videos={}
    for path,w,h in [(NEW,1080,1080),(COMPARE,1920,1030)]:
        streams=probe(path);v=next(s for s in streams if s['codec_type']=='video');a=next(s for s in streams if s['codec_type']=='audio')
        assert (v['width'],v['height'],v['nb_frames'],v['r_frame_rate'])==(w,h,'479','30/1')
        assert abs(float(v['duration'])-float(a['duration']))<1/FPS
        assert float(v['start_time'])==float(a['start_time'])==0
        dec=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],capture_output=True,text=True)
        assert dec.returncode==0 and not dec.stderr
        assert pcm(path)==encoded_audio,'audio differs from accepted v8 AAC decode'
        videos[path.name]={'full_decode_passed':True,'audio_pcm_identical_to_v8':True,'frames':479,'fps':30,'width':w,'height':h,'duration_s':float(v['duration'])}
    errors=[];face_errors=[]
    panel=Image.new('RGB',(1200,440),'white');d=ImageDraw.Draw(panel)
    for j,i in enumerate(indices):
        decoded=frame(NEW,i,1080,1080);ref=np.array(Image.open(OUT/f'speaking/{i:05d}.png'))
        errors.append(float(np.abs(decoded.astype(float)-ref).mean()))
        prev=np.array(Image.open(V8/f'speaking/{i:05d}.png'))
        face_errors.append(int(np.abs(ref[:360].astype(int)-prev[:360].astype(int)).max()))
        xx=j%5*240;yy=j//5*220
        panel.paste(Image.fromarray(decoded).crop((240,200,840,800)).resize((200,200)),(xx,yy+20))
        d.text((xx+5,yy+2),f'{i/FPS:.2f}s Breath {b[i]:.3f}',fill='black')
    assert max(errors)<3 and max(face_errors)<=1,(errors,face_errors)
    panel.save(OUT/'sequence_review.jpg',quality=95)
    comparison_errors=[]
    for i in [0,40,301,478]:
        decoded=frame(COMPARE,i,1920,1030)
        if i==301:Image.fromarray(decoded).save(OUT/'comparison_preview.jpg',quality=95)
        for j,folder in enumerate([V8,OUT]):
            ref=Image.open(folder/f'speaking/{i:05d}.png').crop((210,210,870,870)).resize((960,960),Image.Resampling.LANCZOS)
            comparison_errors.append(float(np.abs(decoded[70:,j*960:(j+1)*960].astype(float)-np.array(ref)).mean()))
    assert max(comparison_errors)<3,comparison_errors
    # Actual visible chest change across the strongest inhalation, independent of head motion.
    strongest=max(ev['inhales'],key=lambda e:e['to']-e['from'])
    a=np.array(Image.open(OUT/f"speaking/{strongest['start_frame']:05d}.png")).astype(float)
    z=np.array(Image.open(OUT/f"speaking/{strongest['end_frame']:05d}.png")).astype(float)
    chest_change=float(np.abs(a[480:800,390:690]-z[480:800,390:690]).mean())
    assert chest_change>.5
    report={'passed':True,'non_breath_csv_and_motion_channels_identical':True,'v8_rig_files_identical':True,
        'inhales':inhale_checks,'positive_steps_outside_pause':0,'range':[float(min(b)),float(max(b))],
        'max_frame_step':float(max(np.abs(delta))),'inhale_rate_range':[min(inhale_rates),max(inhale_rates)],
        'exhale_rate_range':[min(exhale_rates),max(exhale_rates)],'videos':videos,
        'reference_frame_mae':errors,'head_pixel_max_difference_vs_v8':max(face_errors),
        'comparison_reference_mae':comparison_errors,'strongest_inhale_chest_rgb_change':chest_change,
        'human_acceptance':'Pending; numerical checks do not establish naturalness.'}
    write(OUT/'verification.json',report);print(json.dumps(report,indent=2))

if __name__=='__main__':main()
