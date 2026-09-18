"""Verify preserved speech, measured punctuation gaps, motion timing and encoded streams."""
import json,re,subprocess,wave
import numpy as np
from build_sample import OUT,SRC,NEW,FPS,write,sha

def pcm(path):
    with wave.open(str(path),'rb') as w:return np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,w.getnchannels()),w.getframerate()

def main():
    old,sr=pcm(SRC/'N01.wav');new,rate=pcm(OUT/'N01.wav');assert sr==rate
    mapping=json.loads((OUT/'time_map.json').read_text());edits=mapping['edits']
    # Exact PCM equality for every interval outside the edited pauses.
    a=0;b=0;preserved=0
    for e in edits:
        x=round(e['old_start_s']*sr);y=round(e['new_start_s']*sr)
        assert np.array_equal(old[a:x],new[b:y]);preserved+=x-a
        a=round(e['old_end_s']*sr);b=round(e['new_end_s']*sr)
    assert np.array_equal(old[a:],new[b:b+len(old)-a]);preserved+=len(old)-a
    proc=subprocess.run(['ffmpeg','-hide_banner','-i',str(OUT/'N01.wav'),'-af','silencedetect=noise=-40dB:d=0.05','-f','null','-'],capture_output=True,text=True,check=True)
    (OUT/'silence_detection.log').write_text(proc.stderr,encoding='utf-8')
    starts=list(map(float,re.findall(r'silence_start: ([0-9.]+)',proc.stderr)))
    ends=list(map(float,re.findall(r'silence_end: ([0-9.]+)',proc.stderr)))
    measured=[]
    for e in edits:
        a,b=min(zip(starts,ends),key=lambda ab:abs(ab[0]-e['new_start_s']))
        assert abs(a-e['new_start_s'])<.003 and abs(b-a-e['target_s'])<.003
        measured.append({'kind':e['kind'],'start_s':a,'duration_s':b-a,'target_s':e['target_s']})
    import csv
    rows=list(csv.DictReader((OUT/'performance_curve.csv').open(encoding='utf-8')))
    breath=np.array([float(r['breath']) for r in rows]);allowed=np.zeros(len(rows)-1,dtype=bool)
    events=json.loads((OUT/'breath_events.json').read_text())['inhales']
    for e in events:
        a,b=e['start_frame'],e['end_frame'];allowed[a:b]=True
        assert any(p['kind'] in ['period','question'] and p['new_start_s']<a/FPS<b/FPS<p['new_end_s'] for p in edits)
        assert np.all(np.diff(breath[a:b+1])>=-1e-6)
        assert np.abs(new[round(a/FPS*sr):round(b/FPS*sr)].astype(int)).max()<328
    assert not np.any(np.diff(breath)[~allowed]>1e-6)
    assert np.max(np.abs(np.diff(breath)))<.05
    model_files=['Risa_chest_breath.cmo3','Risa_chest_breath.moc3','Risa_chest_breath.cdi3.json','Risa_chest_breath.2048/texture_00.png']
    for name in model_files:assert sha(SRC/'model'/name)==sha(OUT/'model'/name)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(NEW)]))['streams']
    v=next(s for s in probe if s['codec_type']=='video');a=next(s for s in probe if s['codec_type']=='audio')
    assert (v['width'],v['height'],v['r_frame_rate'])==(1080,1080,'30/1')
    assert int(v['nb_frames'])==len(rows) and abs(float(v['duration'])-float(a['duration']))<1/FPS
    assert float(v['start_time'])==float(a['start_time'])==0
    decode=subprocess.run(['ffmpeg','-v','error','-i',str(NEW),'-f','null','-'],capture_output=True,text=True)
    assert decode.returncode==0 and not decode.stderr
    decoded=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(NEW),'-vn','-ar',str(sr),'-ac','2','-f','f32le','-']),'<f4').reshape(-1,2)
    n=min(len(new),len(decoded));corr=float(np.corrcoef(new[:n,0],decoded[:n,0])[0,1]);assert corr>.995
    write(OUT/'verification.json',{'passed':True,'preserved_pcm_seconds':preserved/sr,'speech_pcm_bit_identical':True,
          'measured_gaps':measured,'inhales_only_in_sentence_pauses':True,'unchanged_model_hashes':True,
          'frames':len(rows),'video_duration_s':float(v['duration']),'audio_duration_s':float(a['duration']),
          'encoded_audio_zero_lag_correlation':corr,'full_decode_passed':True,'human_listening':'pending'})
    write(OUT/'manifest.json',{'video':str(NEW),'hashes':{str(p):sha(p) for p in [NEW,OUT/'N01.wav',OUT/'performance_curve.csv',OUT/'performance.motion3.json']}})
    print(json.dumps(json.loads((OUT/'verification.json').read_text()),indent=2))

if __name__=='__main__':main()
