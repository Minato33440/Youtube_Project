"""Local word timing estimates for short source excerpts; not listening QA."""
from pathlib import Path
import json
import subprocess
from faster_whisper import WhisperModel

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'Politics_Economics/2026-09-09_fiscal_policy'
D=P/'code_edit/hook_montage_v1'
D.mkdir(parents=True,exist_ok=True)
model_path=Path('C:/Users/Setona/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120')
model=WhisperModel(str(model_path),device='cpu',compute_type='int8',cpu_threads=8,local_files_only=True)
spans=[('growth','HDIBA7-83yE',148,160),('tax','YXQjMSHSWEo',846,863),('household','VdKZeKSmo8o',884,907)]
result=[]
for cid,vid,a,b in spans:
    wav=D/(cid+'_context.wav')
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(a),'-i',str(P/'media/sources'/f'{vid}.mp4'),
                    '-t',str(b-a),'-ac','1','-ar','16000',str(wav)],check=True)
    segments,info=model.transcribe(str(wav),language='ja',beam_size=5,word_timestamps=True,vad_filter=False)
    rows=[]
    for seg in segments:
        words=[dict(start=round(a+w.start,3),end=round(a+w.end,3),word=w.word,probability=w.probability) for w in seg.words]
        rows.append(dict(start=a+seg.start,end=a+seg.end,text=seg.text,words=words))
        print(cid,round(a+seg.start,2),round(a+seg.end,2),seg.text,flush=True)
        print(' '.join(f"{w['start']:.2f}-{w['end']:.2f}:{w['word']}" for w in words),flush=True)
    result.append(dict(id=cid,source=vid,context_in=a,context_out=b,segments=rows))
(D/'source_word_timings.json').write_text(json.dumps(dict(model='faster-whisper-small',method='local CPU int8; machine estimates, not human listening',clips=result),ensure_ascii=False,indent=2),encoding='utf-8')
