"""Measure source-utterance and v4-audio placement against approved intermediates."""
import json, subprocess
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent; PROJECT=ROOT.parents[2]
SPEECH=PROJECT/'Politics_Economics/2026-09-09_fiscal_policy/speech/sample_v1'
AUDIO=PROJECT/'Politics_Economics/2026-09-09_fiscal_policy/media/sample_v1_risa/audio'
V4=ROOT.parent/'voice_sync_v4/audio_mono_44100_pcm16.wav'
def decode(path):
    return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-ac','1','-ar','1000','-f','s16le','-']),dtype='<i2').astype(float)
def lag(ref, part, expected, radius=600):
    # Normalized envelope correlation in a bounded expected-placement window.
    part=part-part.mean(); denom=np.linalg.norm(part) or 1
    best=None
    for start in range(max(0,expected-radius),min(len(ref)-len(part),expected+radius)+1):
        x=ref[start:start+len(part)]; score=float(np.dot(x-x.mean(),part)/(max(np.linalg.norm(x-x.mean()),1)*denom))
        if best is None or score>best[0]: best=(score,start)
    return best
def main():
    all={}
    for n in ['N01','N02','N03','N04','N05']:
        ref=decode(AUDIO/f'{n}.wav'); parts=[decode(p) for p in sorted(SPEECH.glob(n+'_*.wav'))]
        cursor=0; placements=[]
        for path,part in zip(sorted(SPEECH.glob(n+'_*.wav')),parts):
            score,start=lag(ref,part,cursor); placements.append({'part':path.stem,'expected_start_s':cursor/1000,'measured_start_s':start/1000,'offset_s':(start-cursor)/1000,'correlation':score,'duration_s':len(part)/1000}); cursor+=len(part)
        all[n]={'authoritative_decoded_duration_s':len(ref)/1000,'source_concat_duration_s':cursor/1000,'parts':placements}
    inter=decode(ROOT/'reference_audio/N01_full_timeline.wav'); v4=np.frombuffer(V4.read_bytes(),dtype='<i2').astype(float)[:len(inter)]
    score,start=lag(inter,v4,0,600)
    all['N01_v4_comparison']={'full_export_segment_duration_s':len(inter)/1000,'v4_duration_s':len(v4)/1000,'v4_start_s_in_full_export':start/1000,'offset_s':start/1000,'correlation':score}
    (ROOT/'audio_alignment_report.json').write_text(json.dumps(all,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(all,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
