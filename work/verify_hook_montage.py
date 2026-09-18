from pathlib import Path
import json
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'Politics_Economics/2026-09-09_fiscal_policy'
D=P/'code_edit/hook_montage_v1'
m=json.loads((D/'manifest.json').read_text(encoding='utf-8'))
output=Path(m['output']);checks=[]

def run(args):return subprocess.run(args,capture_output=True,check=True).stdout
def wave(path,start):
    raw=run(['ffmpeg','-v','error','-ss',str(start),'-i',str(path),'-t','1.5','-ac','1','-ar','8000','-f','f32le','-'])
    x=np.frombuffer(raw,dtype='<f4').astype(np.float64);return x-x.mean()

sheet=Image.new('RGB',(1440,900),'#101c2a');draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc',22)
for i,c in enumerate(m['timeline']):
    a=wave(P/'media/sources'/(c['source_id']+'.mp4'),c['a']+.3)
    b=wave(output,c['timeline_in']+.3)
    n=min(len(a),len(b));a=a[:n];b=b[:n];L=1<<(2*n-1).bit_length()
    cc=np.fft.irfft(np.fft.rfft(a,L)*np.conj(np.fft.rfft(b,L)),L)
    lags=np.arange(-400,401);vals=cc[lags%L]/(np.linalg.norm(a)*np.linalg.norm(b));best=int(np.argmax(vals))
    score=float(vals[best]);lag=float(lags[best]/8000)
    checks.append(dict(id=c['id'],waveform_correlation=score,lag_seconds=lag,passed=score>.9 and abs(lag)<.05))
    png=D/(c['id']+'.png')
    run(['ffmpeg','-v','error','-y','-ss',str(c['timeline_in']+1),'-i',str(output),'-frames:v','1',str(png)])
    image=Image.open(png).resize((720,405));x=i%2*720;y=i//2*450
    sheet.paste(image,(x,y+40));draw.text((x+12,y+5),f"{c['id']}   {c['timeline_in']:.2f}s",font=font,fill='white')
# Add the later M01 headline as the sixth frame.
png=D/'M01_second.png'
run(['ffmpeg','-v','error','-y','-ss','6','-i',str(output),'-frames:v','1',str(png)])
# Three rows, two columns.
full=Image.new('RGB',(1440,1350),'#101c2a');full.paste(sheet,(0,0))
last=Image.open(D/'M05.png').resize((720,405));full.paste(last,(0,940))
d=ImageDraw.Draw(full);d.text((12,905),f"M05   {m['timeline'][-1]['timeline_in']:.2f}s",font=font,fill='white')
full.paste(Image.open(png).resize((720,405)),(720,940));d.text((732,905),'M01 / 後半字幕',font=font,fill='white')
full.save(D/'contact_sheet.jpg',quality=94)
assert all(c['passed'] for c in checks)
(D/'audio_placement_qa.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False),flush=True)
